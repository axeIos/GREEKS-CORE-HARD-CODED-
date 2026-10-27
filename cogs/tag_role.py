import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import load_config, save_config, make_v2_logs_embed
import asyncio

class TagRoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_loop.start()

    # FIX: Use 1 GROUP = 1 slot instead of 2 separate commands = 2 slots
    tag = app_commands.Group(name="tag", description="Server Tag role management")

    @tag.command(name="setup", description="Setup SERVER TAG role - uses Discord's clan tag")
    @app_commands.describe(tag_text="Server tag text, e.g. GREEKS", role="Role to give when has server tag")
    @app_commands.default_permissions(administrator=True)
    async def setup_tag_role(self, interaction: discord.Interaction, tag_text: str, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        if "settings" not in cfg:
            cfg["settings"] = {}
        if "tag_role" not in cfg["settings"]:
            cfg["settings"]["tag_role"] = {}
        cfg["settings"]["tag_role"] = {
            "tag": tag_text,
            "role_id": role.id,
            "type": "server_tag"
        }
        save_config(cfg)
        view = make_v2_logs_embed("Server Tag Role Setup", f"Server Tag: **{tag_text}**\nRole: {role.mention}\n\nBot checks:\n- Member's **Server Tag** (clan tag / primary guild)\n- Display name fallback: `{tag_text}`\n\nUse /tag check to scan all members")
        await interaction.followup.send(view=view, ephemeral=True)
        # Check after setup
        count = await self.check_all_members(interaction.guild)
        await interaction.followup.send(f"✅ Initial scan: gave role to {count} members", ephemeral=True)

    @tag.command(name="check", description="Manually check all members for server tag role")
    @app_commands.default_permissions(administrator=True)
    async def check_tags(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        count = await self.check_all_members(interaction.guild)
        await interaction.followup.send(f"✅ Checked all members - gave role to {count} members with server tag", ephemeral=True)

    @tag.command(name="status", description="Show tag role config")
    @app_commands.default_permissions(administrator=True)
    async def tag_status(self, interaction: discord.Interaction):
        cfg = load_config()
        tag_cfg = cfg.get("settings", {}).get("tag_role", {})
        if not tag_cfg:
            await interaction.response.send_message("❌ Not setup. Use /tag setup", ephemeral=True)
            return
        role = interaction.guild.get_role(tag_cfg.get("role_id", 0))
        view = make_v2_logs_embed("Tag Status", f"Tag: `{tag_cfg.get('tag')}`\nRole: {role.mention if role else 'Not found'}\nType: {tag_cfg.get('type')}")
        await interaction.response.send_message(view=view, ephemeral=True)

    def has_server_tag(self, member: discord.Member, tag_text: str):
        tag_lower = tag_text.lower()

        # 1. Check primary_guild (new Discord clan tag system)
        try:
            primary = getattr(member, 'primary_guild', None)
            if primary:
                p_tag = getattr(primary, 'tag', None)
                if p_tag and tag_lower in str(p_tag).lower():
                    return True
                # If primary guild is this guild, they display server tag
                pid = getattr(primary, 'id', None) or getattr(primary, 'identity_guild_id', None)
                if pid and pid == member.guild.id:
                    # They have this guild as primary = has server tag of this guild
                    # Check if tag_text matches guild's tag? If tag_text is in guild name or if we just give role
                    # For GREEKS server, if primary is this guild, give role
                    return True
        except:
            pass

        # 2. Check other possible attributes
        try:
            for attr in ['clan', 'guild_tag', 'clan_tag']:
                obj = getattr(member, attr, None)
                if obj:
                    if tag_lower in str(obj).lower():
                        return True
                    inner = getattr(obj, 'tag', None)
                    if inner and tag_lower in str(inner).lower():
                        return True
        except:
            pass

        # 3. Fallback: display name / username contains tag
        try:
            display = member.display_name.lower()
            username = member.name.lower()
            nick = (member.nick or "").lower()
            if tag_lower in display or tag_lower in username or tag_lower in nick:
                return True
        except:
            pass

        return False

    async def check_member(self, member: discord.Member):
        cfg = load_config()
        tag_cfg = cfg.get("settings", {}).get("tag_role")
        if not tag_cfg:
            return False
        tag = tag_cfg.get("tag", "")
        role_id = tag_cfg.get("role_id")
        if not tag or not role_id:
            return False
        guild = member.guild
        role = guild.get_role(role_id)
        if not role or member.bot:
            return False

        has_tag = self.has_server_tag(member, tag)

        if has_tag:
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Has server tag {tag}")
                    print(f"[TAG] Gave {role} to {member}")
                    return True
                except Exception as e:
                    print(f"[TAG] Failed to give role to {member}: {e}")
        else:
            # Optional: remove role if no longer has tag
            # Uncomment if you want auto-remove
            # if role in member.roles:
            #     try:
            #         await member.remove_roles(role, reason="No longer has server tag")
            #     except:
            #         pass
            pass
        return False

    async def check_all_members(self, guild):
        count = 0
        # Fetch members to get primary_guild data
        try:
            # Ensure members are chunked
            if not guild.chunked:
                await guild.chunk()
        except:
            pass
        
        for member in guild.members:
            if not member.bot:
                if await self.check_member(member):
                    count += 1
                    await asyncio.sleep(0.2)  # Avoid rate limit
        print(f"[TAG] Checked {len(guild.members)} members, gave role to {count}")
        return count

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Check when display name or primary guild changes
        if before.display_name != after.display_name or getattr(before, 'primary_guild', None) != getattr(after, 'primary_guild', None) or before.nick != after.nick:
            await self.check_member(after)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        # Primary guild is on user?
        for guild in self.bot.guilds:
            member = guild.get_member(after.id)
            if member:
                await self.check_member(member)

    @tasks.loop(minutes=15)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.check_all_members(guild)

    def cog_unload(self):
        self.check_loop.cancel()

async def setup(bot):
    await bot.add_cog(TagRoleCog(bot))