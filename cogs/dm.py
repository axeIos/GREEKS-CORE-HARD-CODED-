import discord
from discord.ext import commands
from discord import app_commands
import typing
import asyncio

LOGO = "<:GreeksLogo:1505682080330420244>"

class DMCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dm_member", description="Send a direct message to a specific member")
    @app_commands.describe(
        member="The member to send the DM to",
        message="The message content",
        title="Optional embed title",
        description="Optional embed description"
    )
    @app_commands.default_permissions(administrator=True)
    async def dm_member(self, interaction: discord.Interaction, member: discord.Member, message: str, title: typing.Optional[str] = None, description: typing.Optional[str] = None):
        await interaction.response.defer(ephemeral=True)

        if member.bot:
            await interaction.followup.send("You cannot DM bots.", ephemeral=True)
            return

        try:
            view = discord.ui.LayoutView(timeout=None)
            container = discord.ui.Container()

            if title:
                container.add_item(discord.ui.TextDisplay(f"## {title}"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

            if description:
                container.add_item(discord.ui.TextDisplay(description))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

            container.add_item(discord.ui.TextDisplay(message))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(f"-# From {interaction.guild.name}"))

            view.add_item(container)

            await member.send(view=view)
            await interaction.followup.send(f"DM sent to {member.mention}.", ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(f"Cannot DM {member.mention}. Their DMs are closed.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to DM {member.mention}: {e}", ephemeral=True)

    @app_commands.command(name="dm_everyone", description="Send a direct message to all server members")
    @app_commands.describe(
        message="The message to send to everyone",
        title="Optional embed title",
        description="Optional embed description",
        role="Only DM members with this role (optional)",
        delay="Delay between DMs in seconds (default 1.0)"
    )
    @app_commands.default_permissions(administrator=True)
    async def dm_everyone(self, interaction: discord.Interaction, message: str, title: typing.Optional[str] = None, description: typing.Optional[str] = None, role: typing.Optional[discord.Role] = None, delay: float = 1.0):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        members = []

        for m in guild.members:
            if m.bot:
                continue
            if role and role not in m.roles:
                continue
            members.append(m)

        if not members:
            await interaction.followup.send("No members found with that filter.", ephemeral=True)
            return

        # Confirmation
        confirm_view = discord.ui.LayoutView(timeout=60)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"## DM Everyone Confirmation"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(
            f"You are about to DM **{len(members)}** members.\n\n"
            f"**Message:** {message[:1000]}\n"
            f"**Role filter:** {role.mention if role else 'All members'}\n"
            f"**Delay:** {delay}s per DM\n"
            f"**Estimated time:** {int(len(members) * delay)} seconds"
        ))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        row = discord.ui.ActionRow()
        row.add_item(discord.ui.Button(label="Confirm and Send", style=discord.ButtonStyle.danger, custom_id=f"dm_confirm_{interaction.id}"))
        row.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id=f"dm_cancel_{interaction.id}"))
        container.add_item(row)
        confirm_view.add_item(container)

        await interaction.followup.send(view=confirm_view, ephemeral=True)

        if not hasattr(self.bot, 'dm_pending'):
            self.bot.dm_pending = {}

        self.bot.dm_pending[str(interaction.id)] = {
            "member_ids": [m.id for m in members],
            "message": message,
            "title": title,
            "description": description,
            "delay": delay,
            "guild_id": guild.id
        }

    @app_commands.command(name="dm_role", description="Send a direct message to all members with a specific role")
    @app_commands.describe(
        role="The role to DM",
        message="The message content",
        title="Optional embed title",
        description="Optional embed description"
    )
    @app_commands.default_permissions(administrator=True)
    async def dm_role(self, interaction: discord.Interaction, role: discord.Role, message: str, title: typing.Optional[str] = None, description: typing.Optional[str] = None):
        await self.dm_everyone.callback(self, interaction, message, title, description, role, 1.0)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return

        cid = interaction.data["custom_id"]
        if not cid.startswith("dm_confirm_") and not cid.startswith("dm_cancel_"):
            return

        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
        except:
            return

        is_confirm = cid.startswith("dm_confirm_")
        pending_id = cid.replace("dm_confirm_", "").replace("dm_cancel_", "")

        pending = getattr(self.bot, 'dm_pending', {}).get(pending_id)
        if not pending:
            await interaction.followup.send("This request has expired.", ephemeral=True)
            return

        if not is_confirm:
            del self.bot.dm_pending[pending_id]
            await interaction.followup.send("DM broadcast cancelled.", ephemeral=True)
            return

        # Start broadcast
        guild = self.bot.get_guild(pending["guild_id"])
        if not guild:
            await interaction.followup.send("Guild not found.", ephemeral=True)
            return

        member_ids = pending["member_ids"]
        message_text = pending["message"]
        title = pending["title"]
        desc = pending["description"]
        delay = pending["delay"]

        del self.bot.dm_pending[pending_id]

        await interaction.followup.send(f"Starting DM broadcast to {len(member_ids)} members...", ephemeral=True)

        sent = 0
        failed = 0
        blocked = 0

        for mid in member_ids:
            member = guild.get_member(mid)
            if not member:
                try:
                    member = await guild.fetch_member(mid)
                except:
                    failed += 1
                    continue

            if member.bot:
                continue

            try:
                view = discord.ui.LayoutView(timeout=None)
                container = discord.ui.Container()

                if title:
                    container.add_item(discord.ui.TextDisplay(f"## {title}"))
                    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

                if desc:
                    container.add_item(discord.ui.TextDisplay(desc))
                    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

                container.add_item(discord.ui.TextDisplay(message_text))

                view.add_item(container)
                await member.send(view=view)
                sent += 1

            except discord.Forbidden:
                blocked += 1
            except:
                failed += 1

            await asyncio.sleep(delay)

        # Report
        report_view = discord.ui.LayoutView(timeout=None)
        report_container = discord.ui.Container()
        report_container.add_item(discord.ui.TextDisplay(f"## {LOGO} DM Broadcast Completed"))
        report_container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        report_container.add_item(discord.ui.TextDisplay(
            f"**Sent:** {sent}\n"
            f"**Blocked (DMs closed):** {blocked}\n"
            f"**Failed:** {failed}\n"
            f"**Total:** {len(member_ids)}"
        ))
        report_view.add_item(report_container)

        try:
            await interaction.followup.send(view=report_view, ephemeral=True)
        except:
            pass

async def setup(bot):
    await bot.add_cog(DMCog(bot))