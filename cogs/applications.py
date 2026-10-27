import importlib, asyncio, json, pathlib as pl, os, re, datetime, typing
_d = chr(100)+chr(105)+chr(115)+chr(99)+chr(111)+chr(114)+chr(100)
dc = importlib.import_module(_d)
cmds = importlib.import_module(_d + ".ext.commands")
app_cmds = importlib.import_module(_d + ".app_commands")
from discord.ext import tasks
from utils.helpers import load_config, save_config

QUESTIONS = [
    ("What is your GamerTag?", "Your nickname if accepted"),
    ("How many hours do you have?", "e.g. 2000h"),
    ("How old are you?", "e.g. 18"),
    ("What are your past teams?", "Previous teams / Solo"),
    ("What is your best skill?", "PvP, Raiding, etc"),
    ("Why do you want to join GREEKS?", "Why GREEKS?"),
    ("Why should we choose you?", "What makes you different?"),
    ("Do you have clips? Send link/file or skip", "Links or skip"),
    ("What is your timezone / availability?", "e.g. EU evenings"),
    ("Do you have a mic and can communicate?", "Yes/No"),
    ("Anything else you want to add?", "Optional"),
    ("Are u gonna follow us whatever server we choose?", "Yes/No"),
]

CONFIG_FILE = pl.Path("data/applications_panel.json")
DEFAULT_PANEL = {
    "panel_channel": None,
    "panel_message_id": None,
    "console_review_channel": None,
    "pc_review_channel": None,
    "console_role": None,
    "pc_role": None,
    "accept_logs": None,
    "deny_logs": None,
    "interview_category": None,
    "staff_role": None,
    "recruiting": True,
    "recruiting_message": "We are currently recruiting competitive Rust players!",
}

def load_panel():
    if not CONFIG_FILE.exists():
        return DEFAULT_PANEL.copy()
    try:
        data = json.loads(CONFIG_FILE.read_text())
        for k,v in DEFAULT_PANEL.items():
            if k not in data:
                data[k]=v
        return data
    except:
        return DEFAULT_PANEL.copy()

def save_panel(data):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class ApplicationsCog(cmds.Cog):
    def __init__(self, bot):
        self.bot=bot
        self.active=set()
        self.auto_update_panel.start()

    def cog_unload(self):
        self.auto_update_panel.cancel()

    def build_panel_fast(self, guild: dc.Guild):
        cfg = load_panel()
        console_role_id = cfg.get("console_role")
        pc_role_id = cfg.get("pc_role")
        console_count = 0
        pc_count = 0
        if guild:
            if console_role_id:
                r = guild.get_role(console_role_id)
                if r: 
                    try: console_count = len(r.members)
                    except: console_count = 0
            if pc_role_id:
                r = guild.get_role(pc_role_id)
                if r: 
                    try: pc_count = len(r.members)
                    except: pc_count = 0
        recruiting = cfg.get("recruiting", True)
        recruiting_msg = cfg.get("recruiting_message", "Recruiting")
        view = dc.ui.LayoutView(timeout=None)
        container = dc.ui.Container()
        container.add_item(dc.ui.TextDisplay(f"## GREEKS NETWORK - ELITE RECRUITMENT"))
        container.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        if recruiting:
            container.add_item(dc.ui.TextDisplay(f"**Status:** 🟢 {recruiting_msg}"))
        else:
            container.add_item(dc.ui.TextDisplay(f"**Status:** 🔴 Closed - {recruiting_msg}"))
        container.add_item(dc.ui.TextDisplay(f"**<:console:1561072796568916141> Console:** {console_count} | **<:pc:1561072856748527736> PC:** {pc_count}"))
        container.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.large))
        container.add_item(dc.ui.TextDisplay(f"### What Defines GREEKS"))
        container.add_item(dc.ui.TextDisplay(f"**Domination** - Map control\n**Discipline** - Calls over ego\n**Loyalty** - No team hopping\n**Grind** - We wipe to win"))
        container.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.large))
        console_sec = dc.ui.Section(accessory=dc.ui.Button(label="Apply Console", style=dc.ButtonStyle.primary, custom_id="app_console", emoji=dc.PartialEmoji(name="console", id=1561072796568916141)))
        console_sec.add_item(dc.ui.TextDisplay(f"**<:console:1561072796568916141> Console Division**\nTop 9% console Rust. Main monthly. We contest every event. Expect tryouts, aim tests and teamwork evaluation. No second chances."))
        container.add_item(console_sec)
        container.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        pc_sec = dc.ui.Section(accessory=dc.ui.Button(label="Apply PC", style=dc.ButtonStyle.primary, custom_id="app_pc", emoji=dc.PartialEmoji(name="pc", id=1561072856748527736)))
        pc_sec.add_item(dc.ui.TextDisplay(f"**<:pc:1561072856748527736> PC Division**\nFor players who live to compete. Deep raiding, meta counter-raid specialists, PvP demons. We wipe to win."))
        container.add_item(pc_sec)
        container.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.large))
        container.add_item(dc.ui.TextDisplay(f"### <a:briefcase_resize:1561026634860208239> Requirements"))
        container.add_item(dc.ui.TextDisplay(f"• Proven PvP - **We test it**\n• Team experience\n• Full wipe availability\n• Loyalty"))
        view.add_item(container)
        return view

    @tasks.loop(minutes=2)
    async def auto_update_panel(self):
        try:
            cfg = load_panel()
            ch_id = cfg.get("panel_channel")
            msg_id = cfg.get("panel_message_id")
            if not ch_id or not msg_id: return
            for guild in self.bot.guilds:
                ch = guild.get_channel(ch_id)
                if ch:
                    try:
                        msg = await ch.fetch_message(msg_id)
                        new_view = self.build_panel_fast(guild=guild)
                        await msg.edit(view=new_view)
                    except: pass
                    break
        except: pass

    @auto_update_panel.before_loop
    async def before_auto_update(self):
        await self.bot.wait_until_ready()

    @cmds.Cog.listener()
    async def on_interaction(self, interaction: dc.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        cid=interaction.data["custom_id"]
        if cid in ("app_console", "app_pc"):
            await self.start_application(interaction, cid.split("_")[1])
        elif cid.startswith("accept_") or cid.startswith("deny_") or cid.startswith("interview_") or cid.startswith("ic_") or cid.startswith("ia_"):
            await self.handle_decision(interaction, cid)
        elif cid.startswith("viewapp_"):
            await self.handle_view_app(interaction, cid)

    async def start_application(self, interaction: dc.Interaction, division: str):
        panel_cfg = load_panel()
        if not panel_cfg.get("recruiting", True):
            await interaction.response.send_message(f"Closed: {panel_cfg.get('recruiting_message')}", ephemeral=True)
            return
        if interaction.user.id in self.active:
            await interaction.response.send_message("Already active", ephemeral=True)
            return
        self.active.add(interaction.user.id)
        await interaction.response.send_message(f"Check DMs!", ephemeral=True)
        try:
            dm = await interaction.user.create_dm()
            emoji = "<:console:1561072796568916141>" if division=="console" else "<:pc:1561072856748527736>"
            await dm.send(f"**{emoji} GREEKS {division.upper()} RUST Application**\n{len(QUESTIONS)} questions - `cancel` to cancel")
            answers=[]
            for idx, (q_text, hint) in enumerate(QUESTIONS):
                await dm.send(f"**Question {idx+1}/{len(QUESTIONS)}:** {q_text}\n-# {hint}")
                def check(m): return m.author.id==interaction.user.id and isinstance(m.channel, dc.DMChannel)
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=600)
                    if msg.content.lower().strip()=="cancel":
                        await dm.send("Cancelled")
                        self.active.discard(interaction.user.id)
                        return
                    txt = msg.content.strip() if msg.content else ""
                    urls = [a.url for a in msg.attachments] if msg.attachments else []
                    combined = txt + ("\n" + "\n".join(urls) if urls else "")
                    if not combined: combined="Skipped"
                    answers.append(combined[:1500])
                except asyncio.TimeoutError:
                    await dm.send("Timeout")
                    self.active.discard(interaction.user.id)
                    return
            os.makedirs("data/applications", exist_ok=True)
            gtag = answers[0] if answers else interaction.user.name
            save_data = {"gamer_tag": gtag[:32], "user_id": interaction.user.id, "division": division, "answers": answers, "username": str(interaction.user), "created_at": utc_now().isoformat()}
            pl.Path(f"data/applications/{interaction.user.id}_{division}.json").write_text(json.dumps(save_data))
            main_cfg=load_config()
            if division=="console":
                ch_id = panel_cfg.get("console_review_channel") or main_cfg["channels"].get("applications_review_console")
            else:
                ch_id = panel_cfg.get("pc_review_channel") or main_cfg["channels"].get("applications_review_pc")
            ch = interaction.guild.get_channel(ch_id) if ch_id else None
            if ch:
                review_view = dc.ui.LayoutView()
                rc = dc.ui.Container()
                rc.add_item(dc.ui.TextDisplay(f"## {'<:console:1561072796568916141>' if division=='console' else '<:pc:1561072856748527736>'} GREEKS {division.upper()} RUST"))
                rc.add_item(dc.ui.TextDisplay(f"**User:** {interaction.user.mention}\n**GamerTag:** `{gtag}`\n**Division:** {division.upper()}\n<t:{int(utc_now().timestamp())}:F>"))
                rc.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.large))
                for idx, ans in enumerate(answers):
                    rc.add_item(dc.ui.TextDisplay(f"**{idx+1}. {QUESTIONS[idx][0]}**\n{ans[:1000]}"))
                    if idx < len(answers)-1:
                        rc.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
                rc.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.large))
                row = dc.ui.ActionRow()
                safe_tag = re.sub(r'[^a-zA-Z0-9]', '_', gtag)[:20]
                row.add_item(dc.ui.Button(label="Accept", style=dc.ButtonStyle.success, custom_id=f"accept_{interaction.user.id}_{division}_{safe_tag}"))
                row.add_item(dc.ui.Button(label="Deny", style=dc.ButtonStyle.danger, custom_id=f"deny_{interaction.user.id}_{division}_{safe_tag}"))
                row.add_item(dc.ui.Button(label="Interview", style=dc.ButtonStyle.secondary, custom_id=f"interview_{interaction.user.id}_{division}_{safe_tag}"))
                rc.add_item(row)
                review_view.add_item(rc)
                await ch.send(view=review_view)
            await dm.send(f"Submitted!")
            self.active.discard(interaction.user.id)
        except Exception as e:
            print(f"APP ERROR {e}")
            self.active.discard(interaction.user.id)

    async def handle_view_app(self, interaction: dc.Interaction, cid: str):
        try:
            _, uid, div = cid.split("_")
            uid = int(uid)
        except:
            await interaction.response.send_message("Invalid", ephemeral=True)
            return
        p=pl.Path(f"data/applications/{uid}_{div}.json")
        if not p.exists():
            await interaction.response.send_message("Application not found", ephemeral=True)
            return
        data=json.loads(p.read_text())
        answers = data.get("answers", [])
        gtag = data.get("gamer_tag", f"User-{uid}")
        view = dc.ui.LayoutView()
        c = dc.ui.Container()
        c.add_item(dc.ui.TextDisplay(f"## {gtag} - {div.upper()} Application | <@{uid}>"))
        c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        c.add_item(dc.ui.TextDisplay(f"**User ID:** {uid}\n**Division:** {div.upper()}\n**Submitted:** <t:{int(datetime.datetime.fromisoformat(data.get('created_at', utc_now().isoformat())).timestamp())}:F>"))
        c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.large))
        for idx, ans in enumerate(answers):
            q = QUESTIONS[idx][0] if idx < len(QUESTIONS) else f"Q{idx+1}"
            c.add_item(dc.ui.TextDisplay(f"**{idx+1}. {q}**\n{ans[:1000]}"))
            if idx < len(answers)-1:
                c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

    def build_accept_deny_embed(self, action: str, uid: int, div: str, gamer_tag: str, member, answers, staff_mention: str, guild: dc.Guild, from_interview=False):
        is_accept = action == "accept"
        color = 0x57F287 if is_accept else 0xED4245
        title = "ACCEPTED" if is_accept else "DENIED"
        if from_interview:
            title += " (From Interview)"
        
        now_ts = int(utc_now().timestamp())
        
        # Safe answers
        def get_ans(i):
            if i < len(answers):
                return answers[i][:400]
            return "N/A"
        
        # Dates
        created_at = "N/A"
        joined_at = "N/A"
        if member:
            try:
                created_at = f"<t:{int(member.created_at.timestamp())}:F> (<t:{int(member.created_at.timestamp())}:R>)"
                if member.joined_at:
                    joined_at = f"<t:{int(member.joined_at.timestamp())}:F> (<t:{int(member.joined_at.timestamp())}:R>)"
            except:
                pass
        
        view = dc.ui.LayoutView()
        cont = dc.ui.Container(accent_color=color)
        
        # Title + user
        cont.add_item(dc.ui.TextDisplay(f"## {'✅' if is_accept else '❌'} {title}\n**User:** <@{uid}> {member.mention if member else ''}\n**Username:** `{member.name if member else 'Unknown'}#{member.discriminator if member and member.discriminator!='0' else ''}`\n**User ID:** `{uid}`"))
        cont.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        
        # Core info
        cont.add_item(dc.ui.TextDisplay(
            f"**GamerTag:** `{gamer_tag}`\n"
            f"**Division:** {div.upper()}\n"
            f"**Hours:** {get_ans(1)}\n"
            f"**Age:** {get_ans(2)}\n"
            f"**Timezone / Availability:** {get_ans(8)}\n"
            f"**Mic:** {get_ans(9)}\n"
            f"**Loyalty:** {get_ans(11)}"
        ))
        cont.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        
        # Extended info
        cont.add_item(dc.ui.TextDisplay(
            f"**Past Teams:** {get_ans(3)}\n"
            f"**Best Skill:** {get_ans(4)}\n"
            f"**Clips:** {get_ans(7)}"
        ))
        cont.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        
        cont.add_item(dc.ui.TextDisplay(
            f"**Why GREEKS:** {get_ans(5)[:300]}\n"
            f"**Why Choose:** {get_ans(6)[:300]}\n"
            f"**Extra:** {get_ans(10)[:300]}"
        ))
        cont.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
        
        cont.add_item(dc.ui.TextDisplay(
            f"**Account Created:** {created_at}\n"
            f"**Joined Server:** {joined_at}\n"
            f"**Application Date:** <t:{now_ts}:F>\n"
            f"**Handled By:** {staff_mention}\n"
            f"**From Interview:** {'Yes' if from_interview else 'No'}"
        ))
        cont.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.large))
        
        # Only button, no Q&A on embed
        row = dc.ui.ActionRow()
        row.add_item(dc.ui.Button(label="View Full Application", style=dc.ButtonStyle.secondary, custom_id=f"viewapp_{uid}_{div}"))
        cont.add_item(row)
        
        view.add_item(cont)
        return view

    async def handle_decision(self, interaction: dc.Interaction, cid: str):
        panel_cfg = load_panel()
        staff_role_id = panel_cfg.get("staff_role")
        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role and staff_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(f"Only {staff_role.mention} can do this!", ephemeral=True)
                return
        await interaction.response.defer(ephemeral=True)
        cfg=load_config()

        if cid.startswith("interview_"):
            try:
                parts=cid.split("_"); uid=int(parts[1]); div=parts[2]; safe_tag=parts[3] if len(parts)>3 else "notag"
                guild=interaction.guild
                member=guild.get_member(uid) or await guild.fetch_member(uid)
                category_id=panel_cfg.get("interview_category")
                category=guild.get_channel(category_id) if category_id else interaction.channel.category
                overwrites={
                    guild.default_role: dc.PermissionOverwrite(view_channel=False),
                    member: dc.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True, read_message_history=True),
                    interaction.user: dc.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True, read_message_history=True),
                    guild.me: dc.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
                }
                if staff_role_id:
                    srole = guild.get_role(staff_role_id)
                    if srole:
                        overwrites[srole] = dc.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True, read_message_history=True)
                ch_name=f"interview-{member.name.lower()}-{div}"
                interview_ch=await guild.create_text_channel(name=ch_name, overwrites=overwrites, category=category)
                view = dc.ui.LayoutView()
                c = dc.ui.Container()
                c.add_item(dc.ui.TextDisplay(f"## INTERVIEW - {div.upper()}\n**User:** {member.mention} | `{safe_tag}`\n**Interviewer:** {interaction.user.mention}"))
                c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
                c.add_item(dc.ui.TextDisplay(f"Use buttons below to manage this interview"))
                c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.large))
                row1 = dc.ui.ActionRow()
                row1.add_item(dc.ui.Button(label="View Application", style=dc.ButtonStyle.secondary, custom_id=f"viewapp_{uid}_{div}"))
                row1.add_item(dc.ui.Button(label="Accept", style=dc.ButtonStyle.success, custom_id=f"ia_accept_{uid}_{div}_{safe_tag}"))
                row1.add_item(dc.ui.Button(label="Deny", style=dc.ButtonStyle.danger, custom_id=f"ia_deny_{uid}_{div}_{safe_tag}"))
                c.add_item(row1)
                c.add_item(dc.ui.Separator(spacing=dc.SeparatorSpacing.small))
                row2 = dc.ui.ActionRow()
                row2.add_item(dc.ui.Button(label="Close Interview", style=dc.ButtonStyle.secondary, custom_id=f"ic_close"))
                c.add_item(row2)
                view.add_item(c)
                await interview_ch.send(view=view)
                await interaction.followup.send(f"Interview: {interview_ch.mention}", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Error: {e}", ephemeral=True)
            return

        if cid.startswith("ia_"):
            try:
                parts=cid.split("_")
                action=parts[1]
                uid=int(parts[2])
                div=parts[3]
                safe_tag=parts[4] if len(parts)>4 else "notag"
            except:
                await interaction.followup.send("Invalid", ephemeral=True)
                return
            guild=interaction.guild
            try: member=guild.get_member(uid) or await guild.fetch_member(uid)
            except: member=None
            p=pl.Path(f"data/applications/{uid}_{div}.json")
            gamer_tag=safe_tag.replace("_"," ") if safe_tag!="notag" else (member.display_name if member else f"User-{uid}")
            answers=[]
            if p.exists():
                try:
                    data=json.loads(p.read_text())
                    if data.get("gamer_tag"): gamer_tag=data.get("gamer_tag")
                    answers=data.get("answers", [])
                except: pass
            clean_tag=str(gamer_tag).strip()[:32]
            console_role_id = panel_cfg.get("console_role") or cfg["roles"].get("console_member")
            pc_role_id = panel_cfg.get("pc_role") or cfg["roles"].get("pc_member")
            role_id = console_role_id if div=="console" else pc_role_id
            role=guild.get_role(role_id) if role_id else None
            accept_ch = guild.get_channel(panel_cfg.get("accept_logs")) if panel_cfg.get("accept_logs") else None
            deny_ch = guild.get_channel(panel_cfg.get("deny_logs")) if panel_cfg.get("deny_logs") else None
            if action=="accept":
                if member:
                    try: await member.edit(nick=clean_tag)
                    except: pass
                    if role:
                        try: await member.add_roles(role)
                        except: pass
                if accept_ch:
                    view = self.build_accept_deny_embed("accept", uid, div, clean_tag, member, answers, interaction.user.mention, guild, from_interview=True)
                    await accept_ch.send(view=view)
                await interaction.followup.send(f"Accepted {uid} | {clean_tag} - closing interview in 5s", ephemeral=True)
                await asyncio.sleep(5)
                try: await interaction.channel.delete()
                except: pass
            else:
                if deny_ch:
                    view = self.build_accept_deny_embed("deny", uid, div, clean_tag, member, answers, interaction.user.mention, guild, from_interview=True)
                    await deny_ch.send(view=view)
                await interaction.followup.send(f"Denied {uid} - closing in 5s", ephemeral=True)
                await asyncio.sleep(5)
                try: await interaction.channel.delete()
                except: pass
            return

        if cid.startswith("ic_"):
            await interaction.followup.send("Closing in 5s...", ephemeral=True)
            await asyncio.sleep(5)
            try: await interaction.channel.delete()
            except: pass
            return

        try:
            parts=cid.split("_"); action=parts[0]; uid=int(parts[1]); div=parts[2] if len(parts)>2 else "console"; safe_tag=parts[3] if len(parts)>3 else "notag"
        except:
            await interaction.followup.send("Invalid", ephemeral=True); return
        guild=interaction.guild
        try: member=guild.get_member(uid) or await guild.fetch_member(uid)
        except: member=None
        p=pl.Path(f"data/applications/{uid}_{div}.json")
        gamer_tag=safe_tag.replace("_"," ") if safe_tag!="notag" else (member.display_name if member else f"User-{uid}")
        answers=[]
        if p.exists():
            try:
                data=json.loads(p.read_text())
                if data.get("gamer_tag"): gamer_tag=data.get("gamer_tag")
                answers=data.get("answers", [])
            except: pass
        clean_tag=str(gamer_tag).strip()[:32]
        console_role_id = panel_cfg.get("console_role") or cfg["roles"].get("console_member")
        pc_role_id = panel_cfg.get("pc_role") or cfg["roles"].get("pc_member")
        role_id = console_role_id if div=="console" else pc_role_id
        role=guild.get_role(role_id) if role_id else None
        accept_ch = guild.get_channel(panel_cfg.get("accept_logs")) if panel_cfg.get("accept_logs") else None
        deny_ch = guild.get_channel(panel_cfg.get("deny_logs")) if panel_cfg.get("deny_logs") else None
        try: await interaction.message.delete()
        except: pass
        if action=="accept":
            if member:
                try: await member.edit(nick=clean_tag)
                except: pass
                if role:
                    try: await member.add_roles(role)
                    except: pass
            if accept_ch:
                view = self.build_accept_deny_embed("accept", uid, div, clean_tag, member, answers, interaction.user.mention, guild, from_interview=False)
                await accept_ch.send(view=view)
            await interaction.followup.send(f"Accepted {uid} | {clean_tag}", ephemeral=True)
        else:
            if deny_ch:
                view = self.build_accept_deny_embed("deny", uid, div, clean_tag, member, answers, interaction.user.mention, guild, from_interview=False)
                await deny_ch.send(view=view)
            await interaction.followup.send(f"Denied {uid}", ephemeral=True)
        try:
            cfg_p = load_panel()
            ch_id = cfg_p.get("panel_channel")
            msg_id = cfg_p.get("panel_message_id")
            if ch_id and msg_id:
                ch = guild.get_channel(ch_id)
                if ch:
                    msg = await ch.fetch_message(msg_id)
                    new_view = self.build_panel_fast(guild=guild)
                    await msg.edit(view=new_view)
        except: pass

    @app_cmds.command(name="setup_applications", description="Setup applications system")
    @app_cmds.default_permissions(administrator=True)
    async def setup_applications(self, interaction: dc.Interaction,
        panel_channel: dc.TextChannel,
        console_review_channel: dc.TextChannel,
        pc_review_channel: dc.TextChannel,
        console_role: dc.Role,
        pc_role: dc.Role,
        accept_logs_channel: dc.TextChannel,
        deny_logs_channel: dc.TextChannel,
        staff_role: dc.Role,
        interview_category: typing.Optional[dc.CategoryChannel] = None,
        recruiting_message: typing.Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)
        try:
            cfg = load_panel()
            cfg["panel_channel"] = panel_channel.id
            cfg["console_review_channel"] = console_review_channel.id
            cfg["pc_review_channel"] = pc_review_channel.id
            cfg["console_role"] = console_role.id
            cfg["pc_role"] = pc_role.id
            cfg["accept_logs"] = accept_logs_channel.id
            cfg["deny_logs"] = deny_logs_channel.id
            cfg["staff_role"] = staff_role.id
            if interview_category:
                cfg["interview_category"] = interview_category.id
            if recruiting_message:
                cfg["recruiting_message"] = recruiting_message
            save_panel(cfg)
            main_cfg = load_config()
            main_cfg["channels"]["applications_review_console"] = console_review_channel.id
            main_cfg["channels"]["applications_review_pc"] = pc_review_channel.id
            main_cfg["roles"]["console_member"] = console_role.id
            main_cfg["roles"]["pc_member"] = pc_role.id
            main_cfg["roles"]["staff"] = staff_role.id
            save_config(main_cfg)
            await interaction.followup.send(f"Setup complete - Panel: {panel_channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Setup error: {e}", ephemeral=True)

    @app_cmds.command(name="applications_panel", description="Send recruitment panel")
    @app_cmds.default_permissions(administrator=True)
    async def applications_panel(self, interaction: dc.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            cfg = load_panel()
            ch_id = cfg.get("panel_channel")
            if not ch_id:
                await interaction.followup.send("No panel channel - Use /setup_applications first", ephemeral=True)
                return
            channel = interaction.guild.get_channel(ch_id)
            if not channel:
                await interaction.followup.send("Panel channel not found", ephemeral=True)
                return
            view = self.build_panel_fast(guild=interaction.guild)
            msg = await channel.send(view=view)
            cfg["panel_message_id"] = msg.id
            save_panel(cfg)
            await interaction.followup.send(f"Panel sent in {msg.channel.mention}", ephemeral=True)
        except Exception as e:
            try:
                await interaction.followup.send(f"Error: {e}", ephemeral=True)
            except:
                print(f"PANEL ERROR: {e}")

    @app_cmds.command(name="recruiting_status", description="Update recruiting status")
    @app_cmds.default_permissions(administrator=True)
    async def recruiting_status(self, interaction: dc.Interaction, recruiting: bool, message: typing.Optional[str]=None):
        cfg = load_panel()
        cfg["recruiting"] = recruiting
        if message:
            cfg["recruiting_message"] = message
        save_panel(cfg)
        await interaction.response.send_message(f"Recruiting: {'Open' if recruiting else 'Closed'}", ephemeral=True)

    @app_cmds.command(name="applications_stats", description="Show application stats")
    @app_cmds.default_permissions(administrator=True)
    async def applications_stats(self, interaction: dc.Interaction):
        cfg = load_panel()
        console_role = interaction.guild.get_role(cfg.get("console_role")) if cfg.get("console_role") else None
        pc_role = interaction.guild.get_role(cfg.get("pc_role")) if cfg.get("pc_role") else None
        console_count = len(console_role.members) if console_role else 0
        pc_count = len(pc_role.members) if pc_role else 0
        await interaction.response.send_message(f"Console: {console_count}\nPC: {pc_count}\nTotal: {console_count+pc_count}", ephemeral=True)

async def setup(bot): 
    await bot.add_cog(ApplicationsCog(bot))