import importlib, json, pathlib as pl, datetime, collections, asyncio, typing, re
_d = chr(100)+chr(105)+chr(115)+chr(99)+chr(111)+chr(114)+chr(100)
dc = importlib.import_module(_d)
cmds = importlib.import_module(_d + ".ext.commands")
app_cmds = importlib.import_module(_d + ".app_commands")
from utils.helpers import load_config

# ================= CONFIG =================
BYPASS_ROLE_IDS = [
    111111111111111111,
    222222222222222222,
    333333333333333333,
    444444444444444444,
    555555555555555555,
]

CONFIG_FILE = pl.Path("data/antinuke.json")

# Scam patterns - 【entity-MrBeast¦canonical_name=MrBeast】, Nitro, Steam scam, fake images
SCAM_KEYWORDS = [
    "free nitro", "free discord nitro", "nitro free", "discord gift",
    "mr beast", "【entity-mrbeast¦canonical_name=MrBeast】", "mr beast giveaway", "beast giveaway",
    "steam gift", "free steam", "csgo skin free",
    "airdrop", "crypto giveaway", "double your",
    "nitro from steam", "discord.com/gifts", "discord.gift",
    "@everyone free", "@here free"
]

SCAM_DOMAINS = [
    "disc0rd", "discord-nitro", "steamcommunlty", "steancommunity",
    "discordgift", "disord", "nitro discord", "free-nitro",
    "bit.ly", "tinyurl.com", "discord-app", "discordapp.gift"
]

SCAM_IMAGE_NAMES = [
    "mrbeast", "beast", "nitro", "free", "gift", "steam", "giveaway"
]

LINK_REGEX = re.compile(r"https?://\S+|www\.\S+|discord\.gg/\S+|discord\.com/invite/\S+|discord\.gift/\S+|steamcommunity\.com/\S+")

DEFAULT_CONFIG = {
    "enabled": True,
    "log_channel": None,
    "bypass_roles": BYPASS_ROLE_IDS,
    "punishment": "ban",
    "whitelist_bots": [],
    "time_window": 60,
    "limits": {
        "ban": 3,
        "kick": 3,
        "timeout": 3,
        "channel_delete": 2,
        "channel_create": 3,
        "role_delete": 2,
        "role_create": 3,
        "webhook": 2,
        "bot_add": 1
    },
    "protection": {
        "anti_bot": True,
        "anti_ban": True,
        "anti_kick": True,
        "anti_timeout": True,
        "anti_channel_delete": True,
        "anti_channel_create": True,
        "anti_role_delete": True,
        "anti_role_create": True,
        "anti_webhook": True,
        "anti_scam": True,
        "anti_mrbeast_image": True,
        "anti_everyone_spam": True
    }
}

def load_antinuke():
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CONFIG_FILE.read_text())
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        # Merge nested
        for k in ["limits", "protection"]:
            if k in data:
                for sub_k, sub_v in DEFAULT_CONFIG[k].items():
                    if sub_k not in data[k]:
                        data[k][sub_k] = sub_v
        return data
    except:
        return DEFAULT_CONFIG.copy()

def save_antinuke(data):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))

def is_bypass(member, config):
    if not member: return False
    if member.id == member.guild.owner_id: return True
    bypass_ids = config.get("bypass_roles", BYPASS_ROLE_IDS)
    member_roles = [r.id for r in member.roles]
    return any(rid in member_roles for rid in bypass_ids)

async def send_log(guild, title, desc, color=0xED4245, offender=None, action_type=""):
    cfg = load_antinuke()
    log_id = cfg.get("log_channel")
    if not log_id:
        main = load_config()
        log_id = main["channels"].get("logs")
    if not log_id: return
    ch = guild.get_channel(log_id)
    if not ch: return
    try:
        emoji = dc.PartialEmoji(name="GreeksLogo", id=1505682080330420244)
        view = dc.ui.LayoutView()
        c = dc.ui.Container(accent_color=color)
        c.add_item(dc.ui.TextDisplay(f"## {emoji} {title}"))
        c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        c.add_item(dc.ui.TextDisplay(desc))
        if offender:
            c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
            c.add_item(dc.ui.TextDisplay(f"**Offender:** {offender.mention} ({offender.id})\n**Type:** {action_type}\n**Time:** <t:{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}:F>\n**Punishment:** {cfg.get('punishment','ban').upper()}"))
        view.add_item(c)
        await ch.send(view=view)
    except Exception as e:
        print(f"log err {e}")

async def punish(guild, user, reason):
    cfg = load_antinuke()
    punishment = cfg.get("punishment", "ban")
    try:
        member = guild.get_member(user.id)
        if member and is_bypass(member, cfg):
            return False
        if member:
            try:
                await member.edit(roles=[], reason=f"Anti-Nuke strip: {reason}")
            except: pass
        if punishment == "ban":
            await guild.ban(dc.Object(id=user.id), reason=f"Anti-Nuke: {reason}", delete_message_days=1)
        elif punishment == "kick" and member:
            await member.kick(reason=f"Anti-Nuke: {reason}")
        return True
    except Exception as e:
        print(f"punish err {e}")
        return False

def is_scam_message(content: str, attachments: list):
    content_lower = content.lower()
    # Check keywords
    for kw in SCAM_KEYWORDS:
        if kw in content_lower:
            return True, f"Keyword: {kw}"
    # Check domains
    for dom in SCAM_DOMAINS:
        if dom in content_lower:
            return True, f"Scam domain: {dom}"
    # Check attachments for MrBeast scam images
    for att in attachments:
        name = att.filename.lower()
        for scam_name in SCAM_IMAGE_NAMES:
            if scam_name in name and ("mr" in content_lower or "beast" in content_lower or "nitro" in content_lower or "free" in content_lower):
                return True, f"Scam image: {att.filename}"
        # Check if image contains known scam file types
        if any(x in name for x in [".png", ".jpg", ".jpeg", ".gif"]):
            if any(x in content_lower for x in ["free nitro", "mrbeast", "steam gift", "discord.gift"]):
                return True, f"Scam image + text: {name}"
    return False, ""

class AntiNukeCog(cmds.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = collections.defaultdict(lambda: collections.defaultdict(list))
        self.timeout_cache = collections.defaultdict(list)

    def add_action(self, gid, action, uid):
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        cfg = load_antinuke()
        window = cfg.get("time_window", 60)
        self.cache[gid][action] = [(u,t) for u,t in self.cache[gid][action] if now - t < window]
        self.cache[gid][action].append((uid, now))
        count = sum(1 for u,t in self.cache[gid][action] if u == uid)
        limit = cfg.get("limits", {}).get(action, 3)
        return count, limit, window

    @cmds.Cog.listener()
    async def on_member_ban(self, guild, user):
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_ban"]: return
        await asyncio.sleep(1)
        try:
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.ban):
                if entry.target.id == user.id:
                    off = entry.user
                    if is_bypass(off, cfg): return
                    count, limit, win = self.add_action(guild.id, "ban", off.id)
                    if count >= limit:
                        await punish(guild, off, f"Mass Ban {count}/{limit}")
                        await send_log(guild, "🚨 MASS BAN", f"**Banned:** {user} ({user.id})\n**By:** {off.mention}\n**{count} bans in {win}s (limit {limit})**", 0xED4245, off, "BAN")
                    else:
                        await send_log(guild, "🔨 Ban", f"**User:** {user} ({user.id})\n**By:** {off.mention}\n**Count:** {count}/{limit} in {win}s", 0xFEE75C, off, "BAN")
                    break
        except: pass

    @cmds.Cog.listener()
    async def on_member_remove(self, member):
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_kick"]: return
        await asyncio.sleep(1)
        try:
            guild = member.guild
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.kick):
                if entry.target.id == member.id:
                    off = entry.user
                    if is_bypass(off, cfg): return
                    count, limit, win = self.add_action(guild.id, "kick", off.id)
                    if count >= limit:
                        await punish(guild, off, f"Mass Kick {count}/{limit}")
                        await send_log(guild, "🚨 MASS KICK", f"**Kicked:** {member}\n**By:** {off.mention}\n**{count} kicks in {win}s**", 0xED4245, off, "KICK")
                    break
        except: pass

    @cmds.Cog.listener()
    async def on_member_update(self, before, after):
        # Anti Timeout
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_timeout"]: return
        if before.timed_out_until == after.timed_out_until: return
        if after.timed_out_until is None: return # unmute
        await asyncio.sleep(1)
        try:
            guild = after.guild
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.member_update):
                if entry.target.id == after.id:
                    off = entry.user
                    if is_bypass(off, cfg): return
                    if off.id == after.id: return # self
                    count, limit, win = self.add_action(guild.id, "timeout", off.id)
                    if count >= limit:
                        await punish(guild, off, f"Mass Timeout {count}/{limit}")
                        await send_log(guild, "🚨 MASS TIMEOUT", f"**Timed out:** {after.mention}\n**By:** {off.mention}\n**{count} timeouts in {win}s (limit {limit})**", 0xED4245, off, "TIMEOUT")
                    else:
                        await send_log(guild, "🔇 Timeout", f"**User:** {after.mention}\n**By:** {off.mention}\n**Count:** {count}/{limit}", 0xFEE75C, off, "TIMEOUT")
                    break
        except: pass

    @cmds.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_channel_delete"]: return
        await asyncio.sleep(1)
        try:
            guild = channel.guild
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.channel_delete):
                off = entry.user
                if is_bypass(off, cfg): return
                count, limit, win = self.add_action(guild.id, "channel_delete", off.id)
                if count >= limit:
                    await punish(guild, off, f"Channel Delete {count}/{limit}")
                    await send_log(guild, "🚨 CHANNEL DELETE NUKE", f"**Channel:** #{channel.name}\n**By:** {off.mention}\n**{count}/{limit} in {win}s**", 0xED4245, off, "CHANNEL DELETE")
                break
        except: pass

    @cmds.Cog.listener()
    async def on_guild_channel_create(self, channel):
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_channel_create"]: return
        await asyncio.sleep(1)
        try:
            guild = channel.guild
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    off = entry.user
                    if is_bypass(off, cfg): return
                    count, limit, win = self.add_action(guild.id, "channel_create", off.id)
                    if count >= limit:
                        await punish(guild, off, f"Channel Create spam {count}/{limit}")
                        try: await channel.delete(reason="Anti-Nuke")
                        except: pass
                        await send_log(guild, "🚨 CHANNEL CREATE SPAM", f"**Channel:** {channel.name}\n**By:** {off.mention}\n**{count}/{limit} in {win}s**", 0xED4245, off, "CHANNEL CREATE")
                    break
        except: pass

    @cmds.Cog.listener()
    async def on_guild_role_delete(self, role):
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_role_delete"]: return
        await asyncio.sleep(1)
        try:
            guild = role.guild
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.role_delete):
                off = entry.user
                if is_bypass(off, cfg): return
                count, limit, win = self.add_action(guild.id, "role_delete", off.id)
                if count >= limit:
                    await punish(guild, off, f"Role Delete {count}/{limit}")
                    await send_log(guild, "🚨 ROLE DELETE NUKE", f"**Role:** {role.name}\n**By:** {off.mention}\n**{count}/{limit} in {win}s**", 0xED4245, off, "ROLE DELETE")
                break
        except: pass

    @cmds.Cog.listener()
    async def on_guild_role_create(self, role):
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_role_create"]: return
        await asyncio.sleep(1)
        try:
            guild = role.guild
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.role_create):
                if entry.target.id == role.id:
                    off = entry.user
                    if is_bypass(off, cfg): return
                    count, limit, win = self.add_action(guild.id, "role_create", off.id)
                    if count >= limit:
                        await punish(guild, off, f"Role Create spam")
                        try: await role.delete(reason="Anti-Nuke")
                        except: pass
                        await send_log(guild, "🚨 ROLE CREATE SPAM", f"**Role:** {role.name}\n**By:** {off.mention}", 0xED4245, off, "ROLE CREATE")
                    break
        except: pass

    @cmds.Cog.listener()
    async def on_member_join(self, member):
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_bot"]: return
        if not member.bot: return
        await asyncio.sleep(1)
        try:
            guild = member.guild
            if member.id in cfg.get("whitelist_bots", []): return
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    off = entry.user
                    if is_bypass(off, cfg): return
                    await punish(guild, off, f"Unauthorized bot add {member}")
                    try: await member.ban(reason="Anti-Nuke: Unauthorized bot")
                    except: pass
                    await send_log(guild, "🤖 UNAUTHORIZED BOT", f"**Bot:** {member} ({member.id})\n**By:** {off.mention}", 0xED4245, off, "BOT ADD")
                    break
        except: pass

    @cmds.Cog.listener()
    async def on_webhooks_update(self, channel):
        cfg = load_antinuke()
        if not cfg["enabled"] or not cfg["protection"]["anti_webhook"]: return
        await asyncio.sleep(1)
        try:
            guild = channel.guild
            async for entry in guild.audit_logs(limit=1, action=dc.AuditLogAction.webhook_create):
                off = entry.user
                if is_bypass(off, cfg): return
                count, limit, win = self.add_action(guild.id, "webhook", off.id)
                if count >= limit:
                    await punish(guild, off, f"Webhook spam {count}/{limit}")
                    await send_log(guild, "🚨 WEBHOOK SPAM", f"**Channel:** {channel.mention}\n**By:** {off.mention}\n**{count}/{limit} in {win}s**", 0xED4245, off, "WEBHOOK")
                break
        except: pass

    @cmds.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        cfg = load_antinuke()
        if not cfg["enabled"]: return
        if is_bypass(message.author, cfg): return

        # Anti Scam + MrBeast Image
        if cfg["protection"]["anti_scam"] or cfg["protection"]["anti_mrbeast_image"]:
            is_scam, reason = is_scam_message(message.content, message.attachments)
            if is_scam:
                try: await message.delete()
                except: pass
                try: await message.author.timeout(datetime.timedelta(hours=1), reason=f"Anti-Scam: {reason}")
                except: pass
                await send_log(message.guild, "🚨 SCAM DETECTED", f"**User:** {message.author.mention} ({message.author.id})\n**Reason:** {reason}\n**Content:** {message.content[:500]}\n**Attachments:** {', '.join([a.filename for a in message.attachments])}\n**Action:** Deleted + Timeout 1h", 0xED4245, message.author, f"SCAM: {reason}")
                return

        # Anti @everyone spam
        if cfg["protection"]["anti_everyone_spam"]:
            if "@everyone" in message.content or "@here" in message.content:
                if LINK_REGEX.search(message.content) or len(message.mentions) > 5:
                    try: await message.delete()
                    except: pass
                    await send_log(message.guild, "🚨 @EVERYONE SPAM", f"**User:** {message.author.mention}\n**Content:** {message.content[:500]}", 0xED4245, message.author, "EVERYONE SPAM")

    # ========== ONE COMMAND SETUP ALL ==========
    @app_cmds.command(name="antinuke_setup", description="Setup ALL anti-nuke protection in one command")
    @app_cmds.default_permissions(administrator=True)
    @app_cmds.describe(
        enabled="Enable anti-nuke",
        log_channel="Log channel",
        time_window="Time window in seconds for limits (e.g. 60)",
        punishment="Punishment",
        ban_limit="How many bans trigger nuke",
        kick_limit="How many kicks trigger nuke",
        timeout_limit="How many timeouts trigger nuke",
        channel_delete_limit="Channel deletes trigger",
        channel_create_limit="Channel creates trigger",
        role_delete_limit="Role deletes trigger",
        role_create_limit="Role creates trigger",
        webhook_limit="Webhook creates trigger",
        bypass_role1="Bypass role 1",
        bypass_role2="Bypass role 2",
        bypass_role3="Bypass role 3",
        bypass_role4="Bypass role 4",
        bypass_role5="Bypass role 5"
    )
    async def setup_cmd(
        self,
        interaction: dc.Interaction,
        enabled: bool = True,
        log_channel: typing.Optional[dc.TextChannel] = None,
        time_window: int = 60,
        punishment: typing.Literal["ban", "kick", "strip"] = "ban",
        ban_limit: int = 3,
        kick_limit: int = 3,
        timeout_limit: int = 3,
        channel_delete_limit: int = 2,
        channel_create_limit: int = 3,
        role_delete_limit: int = 2,
        role_create_limit: int = 3,
        webhook_limit: int = 2,
        bypass_role1: typing.Optional[dc.Role] = None,
        bypass_role2: typing.Optional[dc.Role] = None,
        bypass_role3: typing.Optional[dc.Role] = None,
        bypass_role4: typing.Optional[dc.Role] = None,
        bypass_role5: typing.Optional[dc.Role] = None
    ):
        cfg = load_antinuke()
        cfg["enabled"] = enabled
        cfg["punishment"] = punishment
        cfg["time_window"] = time_window
        cfg["limits"]["ban"] = ban_limit
        cfg["limits"]["kick"] = kick_limit
        cfg["limits"]["timeout"] = timeout_limit
        cfg["limits"]["channel_delete"] = channel_delete_limit
        cfg["limits"]["channel_create"] = channel_create_limit
        cfg["limits"]["role_delete"] = role_delete_limit
        cfg["limits"]["role_create"] = role_create_limit
        cfg["limits"]["webhook"] = webhook_limit

        if log_channel:
            cfg["log_channel"] = log_channel.id

        bypass = []
        for r in [bypass_role1, bypass_role2, bypass_role3, bypass_role4, bypass_role5]:
            if r: bypass.append(r.id)
        if bypass:
            cfg["bypass_roles"] = bypass

        save_antinuke(cfg)

        emoji = dc.PartialEmoji(name="GreeksLogo", id=1505682080330420244)
        view = dc.ui.LayoutView()
        c = dc.ui.Container(accent_color=0x57F287 if enabled else 0xED4245)
        bypass_text = ", ".join([f"<@&{rid}>" for rid in cfg["bypass_roles"]]) or "Owner only"
        log_txt = f"<#{cfg['log_channel']}>" if cfg.get("log_channel") else "Default logs"

        c.add_item(dc.ui.TextDisplay(f"## {emoji} Anti-Nuke FULL Setup Complete"))
        c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        c.add_item(dc.ui.TextDisplay(
            f"**Status:** {'🟢 Enabled' if enabled else '🔴 Disabled'}\n"
            f"**Log:** {log_txt}\n"
            f"**Window:** {time_window}s\n"
            f"**Punishment:** {punishment.upper()}\n"
            f"**Bypass (5):** {bypass_text}\n\n"
            f"**YOUR CUSTOM LIMITS:**\n"
            f"🔨 Ban: {ban_limit} in {time_window}s\n"
            f"👢 Kick: {kick_limit} in {time_window}s\n"
            f"🔇 Timeout: {timeout_limit} in {time_window}s\n"
            f"📁 Channel Delete: {channel_delete_limit} / Create: {channel_create_limit} in {time_window}s\n"
            f"🎭 Role Delete: {role_delete_limit} / Create: {role_create_limit} in {time_window}s\n"
            f"🔗 Webhook: {webhook_limit} in {time_window}s\n\n"
            f"**Protection:**\n"
            f"✅ Anti-Ban/Kick/Timeout/Mass | ✅ Channel/Role Delete/Create\n"
            f"✅ Anti-Bot (whitelist) | ✅ Anti-Webhook\n"
            f"✅ Anti-MrBeast Scam Image | ✅ Anti-Nitro/Steam Scam\n"
            f"✅ Anti-@everyone+Link Spam"
        ))
        view.add_item(c)
        await interaction.response.send_message(view=view)

    @app_cmds.command(name="antinuke_status", description="View current anti-nuke config")
    @app_cmds.default_permissions(administrator=True)
    async def status_cmd(self, interaction: dc.Interaction):
        cfg = load_antinuke()
        view = dc.ui.LayoutView()
        c = dc.ui.Container()
        c.add_item(dc.ui.TextDisplay(f"## 🛡️ Anti-Nuke Status\n**Enabled:** {cfg['enabled']}\n**Window:** {cfg['time_window']}s\n**Punishment:** {cfg['punishment']}\n**Limits:** `{cfg['limits']}`\n**Protection:** `{cfg['protection']}`"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_cmds.command(name="antinuke_whitelist", description="Whitelist a bot ID")
    @app_cmds.default_permissions(administrator=True)
    async def whitelist(self, interaction: dc.Interaction, bot_id: str):
        cfg = load_antinuke()
        try:
            bid = int(bot_id)
            if bid not in cfg["whitelist_bots"]:
                cfg["whitelist_bots"].append(bid)
                save_antinuke(cfg)
            await interaction.response.send_message(f"✅ Whitelisted {bid}", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Invalid ID", ephemeral=True)

    @app_cmds.command(name="antinuke_toggle", description="Toggle specific protection on/off")
    @app_cmds.default_permissions(administrator=True)
    async def toggle_cmd(self, interaction: dc.Interaction, protection: typing.Literal["anti_bot","anti_ban","anti_kick","anti_timeout","anti_channel_delete","anti_channel_create","anti_role_delete","anti_role_create","anti_webhook","anti_scam","anti_mrbeast_image","anti_everyone_spam"], enabled: bool):
        cfg = load_antinuke()
        cfg["protection"][protection] = enabled
        save_antinuke(cfg)
        await interaction.response.send_message(f"✅ {protection} = {enabled}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AntiNukeCog(bot))