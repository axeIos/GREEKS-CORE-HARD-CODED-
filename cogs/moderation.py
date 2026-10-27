import importlib, re, json, pathlib as pl, datetime, collections, typing
_d = chr(100)+chr(105)+chr(115)+chr(99)+chr(111)+chr(114)+chr(100)
dc = importlib.import_module(_d)
cmds = importlib.import_module(_d + ".ext.commands")
app_cmds = importlib.import_module(_d + ".app_commands")
app_commands = dc.app_commands
from utils.helpers import load_config

CONFIG_FILE = pl.Path("data/moderation.json")

DEFAULT_CONFIG = {
    "enabled": True,
    "log_channel": None,
    "bypass_roles": [],  # Will be filled via setup
    "punishment": "timeout",
    "settings": {
        "anti_link": True,
        "anti_spam": True,
        "anti_duplicate": True,
        "anti_everyone": True
    },
    "limits": {
        "spam_messages": 5,
        "spam_seconds": 5,
        "spam_punishment_minutes": 10,
        "duplicate_count": 3,
        "duplicate_punishment_minutes": 5,
        "allowed_channel_names": ["ticket", "interview", "tickets", "interviews", "proof"],
        "allowed_channel_ids": [],
        "allowed_links": ["discord.gg", "discord.com/invite", "tiktok.com", "vm.tiktok.com", "instagram.com", "youtube.com", "youtu.be"]
    }
}

def load_mod():
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CONFIG_FILE.read_text())
        for k,v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k]=v
        for k in ["settings","limits"]:
            if k in data:
                for sk, sv in DEFAULT_CONFIG[k].items():
                    if sk not in data[k]:
                        data[k][sk]=sv
        return data
    except:
        return DEFAULT_CONFIG.copy()

def save_mod(data):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))

LINK_REGEX = re.compile(
    r"(https?://\S+|www\.\S+|discord\.gg/\S+|discord\.com/invite/\S+|discord\.me/\S+|discord\.gift/\S+|tiktok\.com/\S+|vm\.tiktok\.com/\S+|instagram\.com/\S+|youtube\.com/\S+|youtu\.be/\S+|t\.me/\S+)",
    re.IGNORECASE
)

def is_bypass(member: dc.Member, cfg: dict):
    if not member or not member.guild:
        return False
    # Owner always bypass
    try:
        if member.id == member.guild.owner_id:
            return True
    except:
        pass
    # Admin bypass
    try:
        if member.guild_permissions.administrator:
            return True
    except:
        pass
    # Manage messages / manage guild bypass (mods)
    try:
        if member.guild_permissions.manage_guild or member.guild_permissions.manage_messages:
            return True
    except:
        pass
    # Role bypass from config
    bypass = cfg.get("bypass_roles", [])
    if not bypass:
        return False
    try:
        member_role_ids = [r.id for r in member.roles]
        for rid in bypass:
            if rid in member_role_ids:
                return True
    except:
        pass
    return False

def is_allowed_channel(channel, cfg):
    if not channel:
        return False
    limits = cfg.get("limits", {})
    allowed_names = limits.get("allowed_channel_names", ["ticket","interview"])
    allowed_ids = limits.get("allowed_channel_ids", [])

    if channel.id in allowed_ids:
        return True

    try:
        name = channel.name.lower()
        if any(allowed.lower() in name for allowed in allowed_names):
            return True
    except:
        pass

    try:
        if hasattr(channel, 'parent') and channel.parent:
            if channel.parent.id in allowed_ids:
                return True
            parent_name = channel.parent.name.lower()
            if any(allowed.lower() in parent_name for allowed in allowed_names):
                return True
    except:
        pass

    try:
        if hasattr(channel, 'category') and channel.category:
            cat_name = channel.category.name.lower()
            if any(allowed.lower() in cat_name for allowed in allowed_names):
                return True
    except:
        pass

    try:
        if hasattr(channel, 'topic') and channel.topic:
            topic = channel.topic.lower()
            if any(allowed.lower() in topic for allowed in allowed_names):
                return True
    except:
        pass

    return False

async def send_log(guild: dc.Guild, title: str, desc: str, color: int = 0xED4245, user: dc.Member = None):
    cfg = load_mod()
    log_id = cfg.get("log_channel")
    if not log_id:
        main = load_config()
        log_id = main.get("channels", {}).get("logs")
    if not log_id:
        return
    ch = guild.get_channel(log_id)
    if not ch:
        try:
            ch = await guild.fetch_channel(log_id)
        except:
            return
    if not ch:
        return
    try:
        emoji = dc.PartialEmoji(name="GreeksLogo", id=1505682080330420244)
        view = dc.ui.LayoutView(timeout=None)
        c = dc.ui.Container()
        c.add_item(dc.ui.TextDisplay(f"## {emoji} {title}"))
        c.add_item(dc.ui.TextDisplay(desc))
        if user:
            c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
            c.add_item(dc.ui.TextDisplay(f"-# User: {user.mention} ({user.id}) | <t:{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}:F>"))
        view.add_item(c)
        await ch.send(view=view)
    except:
        pass

class ModerationCog(cmds.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cache = collections.defaultdict(lambda: collections.deque(maxlen=20))
        self.last_message = {}
        self.dup_count = collections.defaultdict(int)

    @cmds.Cog.listener()
    async def on_message(self, message: dc.Message):
        if message.author.bot or not message.guild:
            return
        cfg = load_mod()
        if not cfg.get("enabled"):
            return

        # FIXED: Bypass check must work - if bypass, skip ALL filters
        if is_bypass(message.author, cfg):
            return

        # ANTI LINK - FIXED
        if cfg["settings"].get("anti_link") and LINK_REGEX.search(message.content):
            if is_allowed_channel(message.channel, cfg):
                return

            try:
                await message.delete()
            except:
                pass
            try:
                view = dc.ui.LayoutView(timeout=None)
                c = dc.ui.Container()
                c.add_item(dc.ui.TextDisplay(f"### ❌ Links not allowed {message.author.mention}\n-# No links in {message.channel.mention} - Use ticket/interview channels"))
                view.add_item(c)
                await message.channel.send(view=view, delete_after=5)
            except:
                pass
            await send_log(message.guild, "🔗 Anti-Link", f"**Channel:** {message.channel.mention} ({message.channel.name})\n**Content:** {message.content[:400]}", 0xED4245, message.author)
            return

        if cfg["settings"].get("anti_spam"):
            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            uid = message.author.id
            self.spam_cache[uid].append(now)
            window = cfg["limits"].get("spam_seconds", 5)
            limit = cfg["limits"].get("spam_messages", 5)
            recent = [t for t in self.spam_cache[uid] if now - t < window]
            if len(recent) >= limit:
                mins = cfg["limits"].get("spam_punishment_minutes", 10)
                try:
                    await message.author.timeout(datetime.timedelta(minutes=mins), reason=f"Anti-Spam: {limit} msgs in {window}s")
                except:
                    pass
                self.spam_cache[uid].clear()
                try:
                    view = dc.ui.LayoutView(timeout=None)
                    c = dc.ui.Container()
                    c.add_item(dc.ui.TextDisplay(f"### ⚠ Anti-Spam\n{message.author.mention} muted {mins}m for spamming ({limit} msgs in {window}s)"))
                    view.add_item(c)
                    await message.channel.send(view=view, delete_after=10)
                except:
                    pass
                await send_log(message.guild, "⚠ Anti-Spam", f"**Channel:** {message.channel.mention}\n**Action:** Timeout {mins}m", 0xFEE75C, message.author)
                return

        if cfg["settings"].get("anti_duplicate"):
            content = message.content.strip().lower()
            if content and len(content) > 4:
                uid = message.author.id
                if uid in self.last_message and self.last_message[uid] == content:
                    self.dup_count[uid] += 1
                    need = cfg["limits"].get("duplicate_count", 3)
                    if self.dup_count[uid] >= need - 1:
                        try:
                            await message.delete()
                        except:
                            pass
                        mins = cfg["limits"].get("duplicate_punishment_minutes", 5)
                        try:
                            await message.author.timeout(datetime.timedelta(minutes=mins), reason="Anti-Duplicate")
                        except:
                            pass
                        await send_log(message.guild, "🔁 Anti-Duplicate", f"**Content:** `{content[:200]}`\n**Action:** Deleted + Timeout {mins}m", 0xFEE75C, message.author)
                        self.dup_count[uid] = 0
                        return
                else:
                    self.dup_count[uid] = 0
                self.last_message[uid] = content

        if cfg["settings"].get("anti_everyone"):
            if ("@everyone" in message.content or "@here" in message.content):
                if LINK_REGEX.search(message.content) or len(message.mentions) > 3:
                    try:
                        await message.delete()
                    except:
                        pass
                    await send_log(message.guild, "🚨 @everyone Spam", f"**Content:** {message.content[:400]}", 0xED4245, message.author)

    @app_cmds.command(name="moderation_setup", description="Setup ALL moderation - FIXED bypass")
    @app_cmds.default_permissions(administrator=True)
    async def moderation_setup(
        self,
        interaction: dc.Interaction,
        enabled: bool = True,
        log_channel: typing.Optional[dc.TextChannel] = None,
        punishment: typing.Literal["timeout","kick","ban"] = "timeout",
        anti_link: bool = True,
        anti_spam: bool = True,
        anti_duplicate: bool = True,
        spam_messages: int = 5,
        spam_seconds: int = 5,
        spam_punishment_minutes: int = 10,
        duplicate_count: int = 3,
        duplicate_punishment_minutes: int = 5,
        allowed_channel_word1: str = "ticket",
        allowed_channel_word2: str = "interview",
        allowed_channel_word3: str = "tickets",
        allowed_channel_word4: str = "proof",
        allowed_channel1: typing.Optional[dc.TextChannel] = None,
        allowed_channel2: typing.Optional[dc.TextChannel] = None,
        allowed_channel3: typing.Optional[dc.TextChannel] = None,
        bypass_role1: typing.Optional[dc.Role] = None,
        bypass_role2: typing.Optional[dc.Role] = None,
        bypass_role3: typing.Optional[dc.Role] = None,
        bypass_role4: typing.Optional[dc.Role] = None,
        bypass_role5: typing.Optional[dc.Role] = None,
        bypass_role6: typing.Optional[dc.Role] = None
    ):
        await interaction.response.defer(ephemeral=True)
        cfg = load_mod()
        cfg["enabled"] = enabled
        cfg["punishment"] = punishment
        cfg["settings"]["anti_link"] = anti_link
        cfg["settings"]["anti_spam"] = anti_spam
        cfg["settings"]["anti_duplicate"] = anti_duplicate
        cfg["limits"]["spam_messages"] = spam_messages
        cfg["limits"]["spam_seconds"] = spam_seconds
        cfg["limits"]["spam_punishment_minutes"] = spam_punishment_minutes
        cfg["limits"]["duplicate_count"] = duplicate_count
        cfg["limits"]["duplicate_punishment_minutes"] = duplicate_punishment_minutes

        words = [allowed_channel_word1.lower(), allowed_channel_word2.lower(), allowed_channel_word3.lower(), allowed_channel_word4.lower()]
        words = [w for w in words if w and w.strip()]
        cfg["limits"]["allowed_channel_names"] = words

        ids = []
        for ch in [allowed_channel1, allowed_channel2, allowed_channel3]:
            if ch:
                ids.append(ch.id)
        if ids:
            cfg["limits"]["allowed_channel_ids"] = ids

        if log_channel:
            cfg["log_channel"] = log_channel.id

        bypass = []
        for r in [bypass_role1, bypass_role2, bypass_role3, bypass_role4, bypass_role5, bypass_role6]:
            if r:
                bypass.append(r.id)
        if bypass:
            cfg["bypass_roles"] = bypass

        save_mod(cfg)

        emoji = dc.PartialEmoji(name="GreeksLogo", id=1505682080330420244)
        view = dc.ui.LayoutView(timeout=None)
        c = dc.ui.Container()
        bypass_text = ", ".join([f"<@&{rid}>" for rid in cfg["bypass_roles"]]) or "Admin/Owner/Manage Messages only"
        log_txt = f"<#{cfg['log_channel']}>" if cfg.get("log_channel") else "Default logs"
        allowed_ids_txt = ", ".join([f"<#{cid}>" for cid in cfg["limits"].get("allowed_channel_ids",[])]) or "None"

        c.add_item(dc.ui.TextDisplay(f"## {emoji} Moderation FIXED Setup"))
        c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        c.add_item(dc.ui.TextDisplay(
            f"**Status:** {'🟢 Enabled' if enabled else '🔴 Disabled'}\n"
            f"**Log:** {log_txt}\n"
            f"**Punishment:** {punishment.upper()}\n"
            f"**Bypass Roles:** {bypass_text}\n"
            f"**Also Bypass:** Owner + Administrator + Manage Messages/Guild\n\n"
            f"**Anti-Link Bypass Channels:**\n"
            f"**By Name:** `{', '.join(cfg['limits']['allowed_channel_names'])}`\n"
            f"**By ID:** {allowed_ids_txt}\n\n"
            f"**Anti-Spam:** {'✅' if anti_spam else '❌'} | `{spam_messages} msgs in {spam_seconds}s = {spam_punishment_minutes}m`\n"
            f"**Anti-Duplicate:** {'✅' if anti_duplicate else '❌'} | `{duplicate_count}x = {duplicate_punishment_minutes}m`\n"
        ))
        view.add_item(c)
        await interaction.followup.send(view=view, ephemeral=True)

    @app_cmds.command(name="moderation_add_bypass", description="Add bypass role for anti-link")
    @app_cmds.default_permissions(administrator=True)
    async def add_bypass(self, interaction: dc.Interaction, role: dc.Role):
        cfg = load_mod()
        if role.id not in cfg["bypass_roles"]:
            cfg["bypass_roles"].append(role.id)
            save_mod(cfg)
        await interaction.response.send_message(f"✅ Added {role.mention} to bypass - now can send links everywhere", ephemeral=True)

    @app_cmds.command(name="moderation_remove_bypass", description="Remove bypass role")
    @app_cmds.default_permissions(administrator=True)
    async def remove_bypass(self, interaction: dc.Interaction, role: dc.Role):
        cfg = load_mod()
        if role.id in cfg["bypass_roles"]:
            cfg["bypass_roles"].remove(role.id)
            save_mod(cfg)
        await interaction.response.send_message(f"✅ Removed {role.mention} from bypass", ephemeral=True)

    @app_cmds.command(name="moderation_add_channel", description="Add channel to anti-link bypass")
    @app_cmds.default_permissions(administrator=True)
    async def add_channel(self, interaction: dc.Interaction, channel: dc.TextChannel):
        cfg = load_mod()
        if "allowed_channel_ids" not in cfg["limits"]:
            cfg["limits"]["allowed_channel_ids"] = []
        if channel.id not in cfg["limits"]["allowed_channel_ids"]:
            cfg["limits"]["allowed_channel_ids"].append(channel.id)
            save_mod(cfg)
        await interaction.response.send_message(f"✅ Added {channel.mention} to bypass - now allows ALL links", ephemeral=True)

    @app_cmds.command(name="moderation_remove_channel", description="Remove channel from bypass")
    @app_cmds.default_permissions(administrator=True)
    async def remove_channel(self, interaction: dc.Interaction, channel: dc.TextChannel):
        cfg = load_mod()
        if channel.id in cfg["limits"].get("allowed_channel_ids", []):
            cfg["limits"]["allowed_channel_ids"].remove(channel.id)
            save_mod(cfg)
        await interaction.response.send_message(f"✅ Removed {channel.mention} from bypass", ephemeral=True)

    @app_cmds.command(name="moderation_status", description="View moderation config")
    @app_cmds.default_permissions(administrator=True)
    async def status(self, interaction: dc.Interaction):
        cfg = load_mod()
        view = dc.ui.LayoutView(timeout=None)
        c = dc.ui.Container()
        c.add_item(dc.ui.TextDisplay(f"## 🛡 Moderation Status\n```json\n{json.dumps(cfg, indent=2)[:1800]}\n```"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_cmds.command(name="clear", description="Clear messages")
    @app_cmds.default_permissions(manage_messages=True)
    async def clear(self, interaction: dc.Interaction, amount: int, user: typing.Optional[dc.Member] = None):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ 1-100 only", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        def check(m):
            return m.author.id == user.id if user else True
        try:
            deleted = await interaction.channel.purge(limit=amount, check=check)
            view = dc.ui.LayoutView(timeout=None)
            cc = dc.ui.Container()
            cc.add_item(dc.ui.TextDisplay(f"### ✅ Cleared {len(deleted)} messages in {interaction.channel.mention}"))
            view.add_item(cc)
            await interaction.followup.send(view=view, ephemeral=True)
            await send_log(interaction.guild, "🧹 Clear", f"**Channel:** {interaction.channel.mention}\n**Amount:** {len(deleted)}", 0x57F287, interaction.user)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

    @app_cmds.command(name="ban", description="Ban member")
    @app_cmds.default_permissions(ban_members=True)
    async def ban_member(self, interaction: dc.Interaction, member: dc.Member, reason: str = "No reason", delete_days: int = 1):
        if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message("❌ Higher role", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            await member.ban(reason=f"{reason} | {interaction.user}", delete_message_days=delete_days)
            view = dc.ui.LayoutView(timeout=None)
            c = dc.ui.Container()
            c.add_item(dc.ui.TextDisplay(f"## 🔨 Banned\n**User:** {member} ({member.id})\n**Reason:** {reason}"))
            view.add_item(c)
            await interaction.followup.send(view=view)
            await send_log(interaction.guild, "🔨 Ban", f"**User:** {member} ({member.id})\n**Reason:** {reason}", 0xED4245, member)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

    @app_cmds.command(name="ban_id", description="Ban by ID")
    @app_cmds.default_permissions(ban_members=True)
    async def ban_id(self, interaction: dc.Interaction, user_id: str, reason: str = "No reason"):
        try:
            uid = int(user_id)
        except:
            await interaction.response.send_message("❌ Invalid ID", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            await interaction.guild.ban(dc.Object(id=uid), reason=f"{reason} | {interaction.user}")
            await interaction.followup.send(f"✅ Banned ID `{uid}`")
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

    @app_cmds.command(name="kick", description="Kick member")
    @app_cmds.default_permissions(kick_members=True)
    async def kick_member(self, interaction: dc.Interaction, member: dc.Member, reason: str = "No reason"):
        if member.top_role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message("❌ Higher role", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            await member.kick(reason=f"{reason} | {interaction.user}")
            view = dc.ui.LayoutView(timeout=None)
            c = dc.ui.Container()
            c.add_item(dc.ui.TextDisplay(f"### 👢 Kicked {member} | Reason: {reason}"))
            view.add_item(c)
            await interaction.followup.send(view=view)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

    @app_cmds.command(name="mute", description="Timeout member")
    @app_cmds.default_permissions(moderate_members=True)
    async def mute(self, interaction: dc.Interaction, member: dc.Member, duration: str = "10m", reason: str = "No reason"):
        units = {"s":1,"m":60,"h":3600,"d":86400}
        try:
            amount = int(duration[:-1])
            sec = amount * units.get(duration[-1].lower(), 60)
            sec = min(sec, 2419200)
            delta = datetime.timedelta(seconds=sec)
        except:
            await interaction.response.send_message("❌ Use 10m, 1h, 1d", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            await member.timeout(delta, reason=f"{reason} | {interaction.user}")
            await interaction.followup.send(f"🔇 Muted {member.mention} for {duration} | {reason}")
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

    @app_cmds.command(name="unmute", description="Unmute member")
    @app_cmds.default_permissions(moderate_members=True)
    async def unmute(self, interaction: dc.Interaction, member: dc.Member):
        await interaction.response.defer()
        try:
            await member.timeout(None, reason=f"Unmuted by {interaction.user}")
            await interaction.followup.send(f"🔊 Unmuted {member.mention}")
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))