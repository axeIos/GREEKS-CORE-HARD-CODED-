import discord, time, os, json, asyncio
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import load_config, save_config
from datetime import datetime, timedelta, timezone

WIPE_FILE = "data/wipe.json"

def load_wipe():
    if not os.path.exists(WIPE_FILE):
        return {"wipe_date": None, "dm_users": [], "channel_id": None, "dm_intervals": {}, "last_dms": {}}
    try:
        with open(WIPE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "dm_intervals" not in data: data["dm_intervals"] = {}
            if "last_dms" not in data: data["last_dms"] = {}
            return data
    except:
        return {"wipe_date": None, "dm_users": [], "channel_id": None, "dm_intervals": {}, "last_dms": {}}

def save_wipe(data):
    os.makedirs("data", exist_ok=True)
    with open(WIPE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_countdown_text(wipe_timestamp: float):
    now = datetime.now(timezone.utc).timestamp()
    diff = wipe_timestamp - now
    if diff <= 0:
        return "🔴 **WIPED!** Server just wiped!", 0, True
    days = int(diff // 86400)
    hours = int((diff % 86400) // 3600)
    mins = int((diff % 3600) // 60)
    if days > 0:
        text = f"⏰ **Wipe in {days}d {hours}h {mins}m**"
    elif hours > 0:
        text = f"⏰ **Wipe in {hours}h {mins}m**"
    else:
        text = f"⏰ **Wipe in {mins}m - GET READY!**"
    return text, diff, False

def get_team_config():
    cfg = load_config()
    if "rust_teams" not in cfg:
        cfg["rust_teams"] = {"invite_allowed_roles": [], "log_channel": None, "team_role_id": None}
        save_config(cfg)
    if "team_role_id" not in cfg["rust_teams"]:
        cfg["rust_teams"]["team_role_id"] = None
    return cfg["rust_teams"]

def save_team_config(team_cfg):
    cfg = load_config()
    cfg["rust_teams"] = team_cfg
    save_config(cfg)

class TeamInviteView(discord.ui.LayoutView):
    def __init__(self, inviter: discord.Member, target: discord.Member, team_role: discord.Role, guild: discord.Guild):
        super().__init__(timeout=86400)
        self.inviter = inviter
        self.target = target
        self.team_role = team_role
        self.guild = guild

        container = discord.ui.Container(accent_color=0x2B2D31)
        container.add_item(discord.ui.TextDisplay(
            f"## 📨 TEAM INVITE - Rust\n"
            f"Hey {target.mention}!\n\n"
            f"**{inviter.display_name}** invited you to join the team!\n\n"
            f"**Team Role you will get:** {team_role.mention} (`{team_role.name}`)\n"
            f"**Server:** {guild.name}\n"
            f"**Invited by:** {inviter.mention} (`{inviter}`)\n\n"
            f"Do you want to accept?\n"
            f"Click **✅ YES** to get the role, or **❌ NO** to decline."
        ))
        self.add_item(container)

        row = discord.ui.ActionRow()
        yes_btn = discord.ui.Button(label="✅ YES - Accept Invite", style=discord.ButtonStyle.success, custom_id="team_yes")
        no_btn = discord.ui.Button(label="❌ NO - Decline", style=discord.ButtonStyle.danger, custom_id="team_no")

        async def yes_callback(interaction: discord.Interaction):
            if interaction.user.id != self.target.id:
                return await interaction.response.send_message("❌ This invite is not for you!", ephemeral=True)
            try:
                member = self.guild.get_member(self.target.id) or await self.guild.fetch_member(self.target.id)
                if not member:
                    return await interaction.response.send_message("❌ Could not find you in the server!", ephemeral=True)
                if self.team_role in member.roles:
                    return await interaction.response.send_message(f"✅ You already have the role {self.team_role.name}!", ephemeral=True)
                await member.add_roles(self.team_role, reason=f"Team invite accepted from {self.inviter} [{self.inviter.id}]")

                view1 = discord.ui.LayoutView()
                c1 = discord.ui.Container(accent_color=0x00FF00)
                c1.add_item(discord.ui.TextDisplay(
                    f"## ✅ TEAM INVITE ACCEPTED\n"
                    f"**User who accepted:** {member.mention} | `{member}` | ID: `{member.id}`\n"
                    f"**Team Role given:** {self.team_role.mention} | `{self.team_role.name}` [{self.team_role.id}]\n"
                    f"**Invited by:** {self.inviter.mention} | `{self.inviter}` | ID: `{self.inviter.id}`\n"
                    f"**At:** <t:{int(time.time())}:F>\n"
                    f"**Answer:** YES ✅ - Role granted automatically"
                ))
                view1.add_item(c1)
                await interaction.response.send_message(view=view1, ephemeral=True)
                try:
                    view_inviter = discord.ui.LayoutView()
                    cc = discord.ui.Container(accent_color=0x00FF00)
                    cc.add_item(discord.ui.TextDisplay(f"## ✅ {member.display_name} accepted your team invite!\n**User:** {member.mention}\n**Team Role:** {self.team_role.mention} (`{self.team_role.name}`)"))
                    view_inviter.add_item(cc)
                    await self.inviter.send(view=view_inviter)
                except: pass
                team_cfg = get_team_config()
                log_ch_id = team_cfg.get("log_channel") or load_config().get("channels", {}).get("logs_moderation") or load_config().get("channels", {}).get("logs")
                if log_ch_id:
                    ch = self.guild.get_channel(log_ch_id)
                    if ch:
                        await ch.send(view=view1, allowed_mentions=discord.AllowedMentions(roles=False))
                self.stop()
            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

        async def no_callback(interaction: discord.Interaction):
            if interaction.user.id != self.target.id:
                return await interaction.response.send_message("❌ This invite is not for you!", ephemeral=True)
            view1 = discord.ui.LayoutView()
            c1 = discord.ui.Container(accent_color=0xFF0000)
            c1.add_item(discord.ui.TextDisplay(
                f"## ❌ TEAM INVITE DECLINED\n"
                f"**User who declined:** {self.target.mention} | `{self.target}` | ID: `{self.target.id}`\n"
                f"**Team Role NOT given:** {self.team_role.name} [{self.team_role.id}]\n"
                f"**Invited by:** {self.inviter.mention} | ID: `{self.inviter.id}`\n"
                f"**At:** <t:{int(time.time())}:F>\n"
                f"**Answer:** NO ❌ - Role not granted"
            ))
            view1.add_item(c1)
            await interaction.response.send_message(view=view1, ephemeral=True)
            self.stop()

        yes_btn.callback = yes_callback
        no_btn.callback = no_callback
        row.add_item(yes_btn)
        row.add_item(no_btn)
        self.add_item(row)

class RustCombinedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dm_reminder_loop.start()
        self.countdown_update_loop.start()

    def cog_unload(self):
        self.dm_reminder_loop.cancel()
        self.countdown_update_loop.cancel()

    def can_invite(self, member: discord.Member):
        if member.guild_permissions.administrator: return True
        if member.id == member.guild.owner_id: return True
        cfg = get_team_config()
        allowed = cfg.get("invite_allowed_roles", [])
        if any(r.id in allowed for r in member.roles): return True
        return False

    @tasks.loop(hours=1)
    async def dm_reminder_loop(self):
        data = load_wipe()
        if not data.get("wipe_date") or not data.get("dm_users"): return
        wipe_ts = data["wipe_date"]
        countdown_text, diff, wiped = get_countdown_text(wipe_ts)
        if wiped: return
        days = int(diff // 86400)
        hours = int((diff % 86400) // 3600)
        mins = int((diff % 3600) // 60)
        intervals = data.get("dm_intervals", {})
        last_dms = data.get("last_dms", {})
        now = time.time()
        changed = False
        for user_id in data["dm_users"][:]:
            user_interval = intervals.get(str(user_id), 2)
            last_dm = last_dms.get(str(user_id), 0)
            if now - last_dm < (user_interval * 3600) - 60: continue
            try:
                user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
                if not user: continue
                view = discord.ui.LayoutView()
                container = discord.ui.Container()
                container.add_item(discord.ui.TextDisplay(f"## ⏰ RUST WIPE REMINDER - Every {user_interval}h"))
                container.add_item(discord.ui.Separator())
                container.add_item(discord.ui.TextDisplay(f"Hey {user.mention}! You selected DM every **{user_interval}h**\n\n**{countdown_text}**\n**Exact:** <t:{int(wipe_ts)}:F> (<t:{int(wipe_ts)}:R>)\n\n**Time left:** {days}d {hours}h {mins}m\n\n🔧 To stop: `/wipe_remind Enable:False` or `/wipe_dm_off`"))
                view.add_item(container)
                try:
                    await user.send(view=view)
                    last_dms[str(user_id)] = now
                    changed = True
                except discord.Forbidden:
                    data["dm_users"].remove(user_id)
                    changed = True
            except Exception as e:
                print(f"DM error {user_id}: {e}")
        if changed:
            data["last_dms"] = last_dms
            save_wipe(data)

    @dm_reminder_loop.before_loop
    async def before_dm_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=30)
    async def countdown_update_loop(self):
        data = load_wipe()
        if not data.get("wipe_date") or not data.get("channel_id"): return
        try:
            channel = self.bot.get_channel(int(data["channel_id"]))
            if not channel: return
            wipe_ts = data["wipe_date"]
            _, diff, wiped = get_countdown_text(wipe_ts)
            if wiped:
                view = discord.ui.LayoutView()
                c = discord.ui.Container()
                c.add_item(discord.ui.TextDisplay(f"## 🔴 SERVER WIPED!\n**Wiped:** <t:{int(wipe_ts)}:F>\nNew wipe not set yet. Use `/wipe_set`"))
                view.add_item(c)
                await channel.send(view=view)
                data["wipe_date"] = None
                save_wipe(data)
        except Exception as e:
            print(f"Countdown update error: {e}")

    @countdown_update_loop.before_loop
    async def before_countdown_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="wipe_set", description="Set Rust wipe date and time")
    @app_commands.default_permissions(administrator=True)
    async def wipe_set(self, interaction: discord.Interaction, date: str, time_hour: int, minute: int = 0, channel: discord.TextChannel = None, timezone_str: str = "Europe/Athens"):
        try:
            from datetime import timedelta
            dt_str = f"{date} {time_hour:02d}:{minute:02d}:00"
            local_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            utc_dt = local_dt - timedelta(hours=3)
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            wipe_timestamp = utc_dt.timestamp()
            if wipe_timestamp < datetime.now(timezone.utc).timestamp():
                return await interaction.response.send_message("❌ Wipe date is in the past!", ephemeral=True)
            data = load_wipe()
            data["wipe_date"] = wipe_timestamp
            if channel: data["channel_id"] = channel.id
            save_wipe(data)
            countdown_text, diff, _ = get_countdown_text(wipe_timestamp)
            days = int(diff // 86400)
            hours = int((diff % 86400) // 3600)
            mins = int((diff % 3600) // 60)
            view = discord.ui.LayoutView()
            c = discord.ui.Container()
            c.add_item(discord.ui.TextDisplay(f"## ✅ WIPE SET!\n**Wipe:** <t:{int(wipe_timestamp)}:F> (<t:{int(wipe_timestamp)}:R>)\n**{countdown_text}**\n**Left:** {days}d {hours}h {mins}m\n**Channel:** {channel.mention if channel else 'Not set'}"))
            view.add_item(c)
            await interaction.response.send_message(view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    @app_commands.command(name="setup_teams", description="Setup team role and who can invite - AUTO ROLE")
    @app_commands.describe(team_role="The team role auto given on YES", role1="Role 1 allowed", role2="Role 2", role3="Role 3", role4="Role 4", role5="Role 5", role6="Role 6", log_channel="Log channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_teams(self, interaction: discord.Interaction, team_role: discord.Role, role1: discord.Role = None, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None, role5: discord.Role = None, role6: discord.Role = None, log_channel: discord.TextChannel = None):
        team_cfg = get_team_config()
        roles = [r for r in [role1, role2, role3, role4, role5, role6] if r]
        team_cfg["team_role_id"] = team_role.id
        team_cfg["invite_allowed_roles"] = [r.id for r in roles]
        if log_channel: team_cfg["log_channel"] = log_channel.id
        save_team_config(team_cfg)
        roles_str = ", ".join([f"{r.name} [{r.id}]" for r in roles]) or "Only admins"
        view = discord.ui.LayoutView()
        c = discord.ui.Container(accent_color=0x2B2D31)
        c.add_item(discord.ui.TextDisplay(f"## 👥 TEAM SETUP - AUTO ROLE (ENGLISH)\n**Team Role:** {team_role.mention} [{team_role.id}]\n**Allowed:** {roles_str}\n**Log:** {log_channel.mention if log_channel else 'Default'}\n\n1. `/team_invite @user` (no role)\n2. Target gets DM YES/NO\n3. YES -> auto gets {team_role.mention}"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.command(name="team_invite", description="Invite a user to your team - auto role")
    @app_commands.describe(member="Who do you want to invite?")
    async def team_invite(self, interaction: discord.Interaction, member: discord.Member):
        if not self.can_invite(interaction.user):
            team_cfg = get_team_config()
            allowed_roles = team_cfg.get("invite_allowed_roles", [])
            allowed_str = ", ".join([f"{interaction.guild.get_role(rid).name}" for rid in allowed_roles if interaction.guild.get_role(rid)]) or "Only Admins"
            return await interaction.response.send_message(f"❌ No permission!\n**Allowed:** {allowed_str}", ephemeral=True)

        team_cfg = get_team_config()
        team_role_id = team_cfg.get("team_role_id")
        if not team_role_id:
            return await interaction.response.send_message("❌ Team role not set! Use `/setup_teams team_role:@Team` first!", ephemeral=True)
        team_role = interaction.guild.get_role(team_role_id)
        if not team_role:
            return await interaction.response.send_message(f"❌ Role {team_role_id} not found! Setup again.", ephemeral=True)
        if member.bot: return await interaction.response.send_message("❌ Cannot invite bot!", ephemeral=True)
        if member.id == interaction.user.id: return await interaction.response.send_message("❌ Cannot invite yourself!", ephemeral=True)
        if team_role in member.roles: return await interaction.response.send_message(f"❌ {member.mention} already has {team_role.mention}!", ephemeral=True)
        if team_role >= interaction.guild.me.top_role: return await interaction.response.send_message("❌ Role higher than bot!", ephemeral=True)

        view = TeamInviteView(interaction.user, member, team_role, interaction.guild)
        try:
            await member.send(view=view)
        except:
            try:
                await interaction.channel.send(f"{member.mention} - DMs closed, invite here:", view=view)
            except:
                return await interaction.response.send_message(f"❌ {member.mention} DMs closed!", ephemeral=True)

        view_log = discord.ui.LayoutView()
        c = discord.ui.Container(accent_color=0x2B2D31)
        c.add_item(discord.ui.TextDisplay(f"## 📨 TEAM INVITE SENT - PENDING\n**Target:** {member.mention} | ID: `{member.id}`\n**Team Role (auto on YES):** {team_role.mention} [{team_role.id}]\n**By:** {interaction.user.mention}\n**Status:** ⏳ Waiting YES/NO\n**At:** <t:{int(time.time())}:F>"))
        view_log.add_item(c)
        await interaction.response.send_message(view=view_log, ephemeral=True)

    @app_commands.command(name="team_setup_status", description="Show team setup")
    async def team_setup_status(self, interaction: discord.Interaction):
        team_cfg = get_team_config()
        allowed = team_cfg.get("invite_allowed_roles", [])
        team_role_id = team_cfg.get("team_role_id")
        team_role = interaction.guild.get_role(team_role_id) if team_role_id else None
        allowed_str = "\n".join([f"- {interaction.guild.get_role(rid).name} [{rid}]" for rid in allowed if interaction.guild.get_role(rid)]) or "Only Admins"
        view = discord.ui.LayoutView()
        c = discord.ui.Container(accent_color=0x2B2D31)
        c.add_item(discord.ui.TextDisplay(f"## 👥 TEAM SETUP STATUS\n**Team Role:** {team_role.mention if team_role else 'NOT SET'} [{team_role_id or 'N/A'}]\n**Allowed:**\n{allowed_str}\n\n`/team_invite @user` - auto gives {team_role.mention if team_role else 'role'}"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RustCombinedCog(bot))