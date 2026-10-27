import discord
import re
import aiohttp
import time
from discord.ext import commands
from discord import app_commands
from utils.helpers import load_config

EMOJI_REGEX = re.compile(r'<(a)?:([a-zA-Z0-9_]+):([0-9]+)>')

class EmojiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="steal_emoji", description="Steal an emoji from another server")
    @app_commands.describe(
        emoji="The emoji you want to steal (e.g. :pepe: or <:name:id>)",
        name="New name for the emoji (optional)",
        image_url="Direct image URL if you don't have an emoji"
    )
    async def steal_emoji(self, interaction: discord.Interaction, emoji: str = None, name: str = None, image_url: str = None):
        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            await interaction.response.send_message("You need Manage Emojis permission to use this command.", ephemeral=True)
            return

        if not emoji and not image_url:
            await interaction.response.send_message(
                "Please provide an emoji! Example:\n"
                "`/steal_emoji emoji:😎`\n"
                "`/steal_emoji emoji:<:pepe:123456> name:pepe`\n"
                "Or with URL: `/steal_emoji image_url:https://... name:myemoji`",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            match = EMOJI_REGEX.search(emoji) if emoji else None
            emoji_id = None
            emoji_name = None
            is_animated = False
            image_data = None

            if match:
                is_animated = bool(match.group(1))
                emoji_name = match.group(2)
                emoji_id = match.group(3)
                final_name = name or emoji_name
                final_name = re.sub(r'[^a-zA-Z0-9_]', '', final_name)[:32]
                if len(final_name) < 2:
                    final_name = f"emoji_{emoji_id[:8]}"

                ext = "gif" if is_animated else "png"
                url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=256&quality=lossless"

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            other_ext = "png" if is_animated else "gif"
                            url2 = f"https://cdn.discordapp.com/emojis/{emoji_id}.{other_ext}"
                            async with session.get(url2) as resp2:
                                if resp2.status != 200:
                                    await interaction.followup.send(f"Could not download emoji. Status {resp.status}", ephemeral=True)
                                    return
                                image_data = await resp2.read()
                        else:
                            image_data = await resp.read()

            elif image_url:
                final_name = name or f"emoji_{int(time.time())}"
                final_name = re.sub(r'[^a-zA-Z0-9_]', '', final_name)[:32]
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status != 200:
                            await interaction.followup.send("Invalid image URL.", ephemeral=True)
                            return
                        image_data = await resp.read()
                is_animated = image_url.endswith(".gif")

            else:
                await interaction.followup.send(
                    f"This is a unicode emoji `{emoji}` - I cannot steal unicode emojis.\n"
                    f"Please provide a custom emoji like `<:name:id>` from another server, or use `image_url`.",
                    ephemeral=True
                )
                return

            if len(interaction.guild.emojis) >= interaction.guild.emoji_limit:
                await interaction.followup.send(
                    f"Server has reached max emoji limit ({interaction.guild.emoji_limit}). Delete some emojis first.",
                    ephemeral=True
                )
                return

            try:
                new_emoji = await interaction.guild.create_custom_emoji(
                    name=final_name,
                    image=image_data,
                    reason=f"Emoji stolen by {interaction.user} - Original: {emoji or image_url}"
                )
            except discord.HTTPException as e:
                if "Maximum number of emojis" in str(e):
                    await interaction.followup.send(f"Max emojis reached. {e}", ephemeral=True)
                    return
                elif "too large" in str(e).lower():
                    await interaction.followup.send(f"File is too large. Must be under 256KB (yours is {len(image_data)//1024}KB).", ephemeral=True)
                    return
                else:
                    await interaction.followup.send(f"Error creating emoji: {e}", ephemeral=True)
                    return

            cfg = load_config()
            log_ch_id = cfg.get("channels", {}).get("logs_moderation") or cfg.get("channels", {}).get("logs")

            if log_ch_id:
                ch = interaction.guild.get_channel(log_ch_id)
                if ch:
                    view_log = discord.ui.LayoutView(timeout=None)
                    c = discord.ui.Container()
                    c.add_item(discord.ui.TextDisplay(f"## Emoji Stolen"))
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    c.add_item(discord.ui.TextDisplay(
                        f"**New Emoji:** {new_emoji} {new_emoji.name} [{new_emoji.id}]\n"
                        f"**Animated:** {'Yes' if new_emoji.animated else 'No'}\n"
                        f"**Original:** {emoji or image_url}\n"
                        f"**Stolen by:** {interaction.user.mention} ({interaction.user.id})\n"
                        f"**At:** <t:{int(time.time())}:F>"
                    ))
                    view_log.add_item(c)
                    try:
                        await ch.send(view=view_log, allowed_mentions=discord.AllowedMentions(roles=False))
                    except:
                        pass

            view = discord.ui.LayoutView(timeout=None)
            cc = discord.ui.Container()
            cc.add_item(discord.ui.TextDisplay(f"## Emoji Stolen Successfully"))
            cc.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            cc.add_item(discord.ui.TextDisplay(
                f"**Emoji:** {new_emoji} `:{new_emoji.name}:`\n"
                f"**Name:** {new_emoji.name}\n"
                f"**ID:** {new_emoji.id}\n"
                f"**Use:** `:{new_emoji.name}:`"
            ))
            view.add_item(cc)
            await interaction.followup.send(view=view, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    @app_commands.command(name="steal_from_message", description="Steal all emojis from a message")
    @app_commands.describe(message_id="Message ID that contains emojis", channel="Channel where the message is located")
    async def steal_emoji_from_message(self, interaction: discord.Interaction, message_id: str, channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            await interaction.response.send_message("You need Manage Emojis permission.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            ch = channel or interaction.channel
            try:
                msg = await ch.fetch_message(int(message_id))
            except:
                await interaction.followup.send(f"Could not find message with ID {message_id}.", ephemeral=True)
                return

            matches = list(EMOJI_REGEX.finditer(msg.content))
            if not matches:
                await interaction.followup.send("No custom emojis found in that message. Must be like `<:name:id>`.", ephemeral=True)
                return

            stolen = []
            failed = []

            async with aiohttp.ClientSession() as session:
                for m in matches[:10]:
                    is_animated = bool(m.group(1))
                    emoji_name = m.group(2)
                    emoji_id = m.group(3)
                    ext = "gif" if is_animated else "png"
                    url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=256"

                    try:
                        async with session.get(url) as resp:
                            if resp.status != 200:
                                failed.append(emoji_name)
                                continue
                            img = await resp.read()

                        if len(interaction.guild.emojis) >= interaction.guild.emoji_limit:
                            failed.append(f"{emoji_name} - max limit")
                            continue

                        final_name = re.sub(r'[^a-zA-Z0-9_]', '', emoji_name)[:32] or f"emoji_{emoji_id[:5]}"
                        new_emoji = await interaction.guild.create_custom_emoji(name=final_name, image=img, reason=f"Mass stolen from {message_id} by {interaction.user}")
                        stolen.append(f"{new_emoji} `:{new_emoji.name}:`")
                    except Exception as e:
                        failed.append(f"{emoji_name}: {e}")

            view = discord.ui.LayoutView(timeout=None)
            c = discord.ui.Container()
            c.add_item(discord.ui.TextDisplay(f"## Mass Steal Completed"))
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(discord.ui.TextDisplay(
                f"**Stolen:** {len(stolen)}/{len(matches)}\n\n"
                f"**Success:**\n{', '.join(stolen) or 'None'}\n\n"
                f"**Failed:**\n{', '.join(failed) or 'None'}"
            ))
            view.add_item(c)
            await interaction.followup.send(view=view, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    @app_commands.command(name="emoji_list", description="Show all emojis in the server")
    async def emoji_list(self, interaction: discord.Interaction):
        emojis = interaction.guild.emojis
        if not emojis:
            await interaction.response.send_message("No emojis found in this server.", ephemeral=True)
            return

        desc = ""
        for e in emojis[:50]:
            desc += f"{e} `:{e.name}:` [{e.id}] {'Animated' if e.animated else ''}\n"

        if len(emojis) > 50:
            desc += f"\n... and {len(emojis) - 50} more"

        view = discord.ui.LayoutView(timeout=None)
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## Emoji List - {len(emojis)}/{interaction.guild.emoji_limit}\n{desc}"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmojiCog(bot))