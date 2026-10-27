import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import load_config, save_config
import datetime

LOGO = "<:GreeksLogo:1505682080330420244>"

class TeamStatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.team_status_loop.start()

    def cog_unload(self):
        self.team_status_loop.cancel()

    @tasks.loop(minutes=2)  # ✅ UPDATE EVERY 2 MINUTES - GUARANTEED
    async def team_status_loop(self):
        await self.bot.wait_until_ready()
        cfg = load_config()
        ch_id = cfg["channels"].get("team_status")
        role_id = cfg["roles"].get("team_status_role")
        if not ch_id or not role_id:
            print(f"[TeamStatus] Missing channel or role config")
            return
        try:
            ch_id = int(ch_id)
            role_id = int(role_id)
        except:
            return
        for g in self.bot.guilds:
            ch = g.get_channel(ch_id)
            if ch:
                print(f"[TeamStatus] Auto-updating every 2 minutes in {g.name}...")
                await self.update_team_status(ch, role_id)

    def get_status(self, member: discord.Member):
        return str(member.status).lower()

    async def get_all_members_with_role(self, guild: discord.Guild, role_id: int):
        role = guild.get_role(role_id)
        if not role:
            return []
        try:
            if not guild.chunked:
                await guild.chunk(cache=True)
        except:
            pass
        # Fetch all if cache incomplete
        if len(guild.members) < guild.member_count:
            try:
                fetched = []
                async for member in guild.fetch_members(limit=None):
                    fetched.append(member)
                all_with_role = [m for m in fetched if role in m.roles]
                if all_with_role:
                    return all_with_role
            except Exception as e:
                print(f"[TeamStatus] Fetch failed: {e}")
        # Fallback
        if len(role.members) > 0:
            return role.members
        return [m for m in guild.members if role in m.roles]

    async def update_team_status(self, channel, role_id=None):
        guild = channel.guild
        cfg = load_config()
        cfg_role_id = role_id or cfg["roles"].get("team_status_role")
        if not cfg_role_id:
            return
        try:
            cfg_role_id = int(cfg_role_id)
        except:
            return
        role = guild.get_role(cfg_role_id)
        if not role:
            return

        members = await self.get_all_members_with_role(guild, cfg_role_id)
        online = [m for m in members if self.get_status(m) == "online"]
        idle = [m for m in members if self.get_status(m) == "idle"]
        dnd = [m for m in members if self.get_status(m) == "dnd"]
        offline = [m for m in members if self.get_status(m) not in ("online", "idle", "dnd")]

        total = len(members)
        online_count = len(online) + len(idle) + len(dnd)
        offline_count = len(offline)

        view = discord.ui.LayoutView(timeout=None)
        container = discord.ui.Container()

        container.add_item(discord.ui.TextDisplay(f"### {LOGO} GREEKS X HOSTILE - TEAM STATUS"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"**Role:** `{role.name}` | **Total:** `{total}` | **Online:** `{online_count}` | **Offline:** `{offline_count}`"))
        container.add_item(discord.ui.TextDisplay(f"-# Last updated: <t:{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}:R> • Next update in 2 minutes"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

        def member_line(m):
            return f"{m.mention} - `{m.display_name[:30]}`"

        if online:
            container.add_item(discord.ui.TextDisplay(f"🟢 **Online — {len(online)}**"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            for m in sorted(online, key=lambda x: x.display_name.lower()):
                container.add_item(discord.ui.TextDisplay(member_line(m)))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        if idle:
            container.add_item(discord.ui.TextDisplay(f"🌙 **Idle — {len(idle)}**"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            for m in sorted(idle, key=lambda x: x.display_name.lower()):
                container.add_item(discord.ui.TextDisplay(member_line(m)))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        if dnd:
            container.add_item(discord.ui.TextDisplay(f"🔴 **Do Not Disturb — {len(dnd)}**"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            for m in sorted(dnd, key=lambda x: x.display_name.lower()):
                container.add_item(discord.ui.TextDisplay(member_line(m)))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        if offline:
            container.add_item(discord.ui.TextDisplay(f"⚫ **Offline — {len(offline)}**"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            for m in sorted(offline, key=lambda x: x.display_name.lower()):
                container.add_item(discord.ui.TextDisplay(member_line(m)))

        if not members:
            container.add_item(discord.ui.TextDisplay(f"⚠️ No members found with role {role.mention}"))

        view.add_item(container)

        try:
            async for msg in channel.history(limit=30):
                if msg.author == self.bot.user:
                    await msg.edit(view=view)
                    print(f"[TeamStatus] ✅ Updated {total} members at {datetime.datetime.now()}")
                    return
            await channel.send(view=view)
            print(f"[TeamStatus] ✅ Sent {total} members")
        except Exception as e:
            print(f"[TeamStatus] Error: {e}")

    @app_commands.command(name="team_status", description="Update team status panel now")
    @app_commands.default_permissions(administrator=True)
    async def team_status_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        ch_id = cfg["channels"].get("team_status")
        role_id = cfg["roles"].get("team_status_role")
        if not ch_id:
            await interaction.followup.send("Team status channel not set", ephemeral=True)
            return
        ch = interaction.guild.get_channel(int(ch_id))
        await self.update_team_status(ch, role_id)
        await interaction.followup.send(f"✅ Updated in {ch.mention} - Auto updates every 2 minutes", ephemeral=True)

    @app_commands.command(name="team_status_role", description="Set which role to track")
    @app_commands.describe(role="Role to track")
    @app_commands.default_permissions(administrator=True)
    async def set_team_role(self, interaction: discord.Interaction, role: discord.Role):
        cfg = load_config()
        if "roles" not in cfg:
            cfg["roles"] = {}
        cfg["roles"]["team_status_role"] = role.id
        save_config(cfg)
        members = await self.get_all_members_with_role(interaction.guild, role.id)
        view = discord.ui.LayoutView(timeout=None)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"## {LOGO} Role Set\n**Role:** {role.mention}\n**Members:** {len(members)}\n**Auto-update:** Every 2 minutes"))
        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)
        ch_id = cfg["channels"].get("team_status")
        if ch_id:
            ch = interaction.guild.get_channel(int(ch_id))
            if ch:
                await self.update_team_status(ch, role.id)

async def setup(bot):
    await bot.add_cog(TeamStatusCog(bot))