import discord
from discord.ext import commands
from discord import app_commands
import json, os, io
from datetime import datetime

CONFIG_PATH = "config.json"
BANNER_URL = "https://cdn.discordapp.com/attachments/1551421560215179367/1555275940056268861/giphy.gif?backend=b2&ex=6abfef17&is=6abe9d97&hm=326e9bf181ab4c1f0a4d0db99fceb041a9a47468745acb78a1202d17dfbef4f5&"

BLUE_TICKET = "<:blue_ticket1:1562150329007607940>"
LOGO = "<:GreeksLogo:1505682080330420244>"
BRIEFCASE = "<a:briefcase_resize:1561026634860208239>"

def load_config():
    default = {"roles": {"ticket_roles": []}, "channels": {"ticket_logs": None, "transcript": None, "category": None}}
    if not os.path.exists(CONFIG_PATH):
        return default
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

class IssueModal(discord.ui.Modal):
    def __init__(self, cat):
        super().__init__(title=f"{cat} Ticket")
        self.cat = cat
        self.issue = discord.ui.TextInput(label="What is your issue?", style=discord.TextStyle.paragraph, max_length=1000)
        self.add_item(self.issue)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        c = i.client.get_cog("TicketsCog")
        if c:
            await c.create_ticket(i, self.cat, self.issue.value)

class PingMemberModal(discord.ui.Modal, title="Ping Member"):
    def __init__(self, ticket_channel_id):
        super().__init__()
        self.ticket_channel_id = ticket_channel_id
        self.member_input = discord.ui.TextInput(label="Member ID or @mention", placeholder="Ex: 123456789 or @user", required=True, max_length=100)
        self.reason = discord.ui.TextInput(label="Reason / Message", style=discord.TextStyle.paragraph, placeholder="Why you pinging him?", required=False, max_length=500)
        self.add_item(self.member_input)
        self.add_item(self.reason)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        raw = self.member_input.value.strip()
        if raw.startswith("<@"):
            raw = raw.replace("<@!", "").replace("<@", "").replace(">", "")
        try:
            target_id = int(''.join(filter(str.isdigit, raw)))
        except:
            target_id = None
        if not target_id:
            await interaction.followup.send("Invalid member.", ephemeral=True)
            return
        try:
            member = guild.get_member(target_id) or await guild.fetch_member(target_id)
        except:
            member = None
        if not member:
            await interaction.followup.send("Den vrika member.", ephemeral=True)
            return
        ticket_ch = guild.get_channel(self.ticket_channel_id)
        msg_text = self.reason.value or "You have been pinged to this ticket!"
        ping_view = discord.ui.LayoutView(timeout=None)
        ping_cont = discord.ui.Container()
        ping_cont.add_item(discord.ui.TextDisplay(f"### {BLUE_TICKET} Member Pinged\n{member.mention} pinged by {interaction.user.mention}\n-# **Reason:** {msg_text}"))
        ping_view.add_item(ping_cont)
        await ticket_ch.send(view=ping_view)
        try:
            dm_view = discord.ui.LayoutView(timeout=None)
            dm_cont = discord.ui.Container()
            dm_cont.add_item(discord.ui.TextDisplay(f"## {BLUE_TICKET} You've Been Pinged\n**Ticket:** {ticket_ch.name}\n**By:** {interaction.user.mention}\n\n**Message:**\n```{msg_text}```\n-# Greeks Network {LOGO}"))
            dm_view.add_item(dm_cont)
            await member.send(view=dm_view)
            dm_status = "DM sent"
        except:
            dm_status = "DM closed"
        await interaction.followup.send(f"{member.mention} pinged! {dm_status}", ephemeral=True)

class TopPanelView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        cont = discord.ui.Container()

        # GIF - Keep as is
        gallery = discord.ui.MediaGallery()
        gallery.add_item(media=BANNER_URL)
        cont.add_item(gallery)

        # Title - NO EMOJIS as requested
        cont.add_item(discord.ui.TextDisplay(f"## GREEKS NETWORK — TICKETS"))
        
        cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

        # TEAM - With briefcase emoji
        cont.add_item(discord.ui.TextDisplay(
            f"### {BRIEFCASE} Team Applications\n"
            f"Want to ask something about us or join our team? Open a ticket here — even if you know people who want to join."
        ))
        r1 = discord.ui.ActionRow()
        r1.add_item(discord.ui.Button(label="Team", style=discord.ButtonStyle.secondary, custom_id="ticket_team"))
        cont.add_item(r1)

        cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        # MERGE - With logo
        cont.add_item(discord.ui.TextDisplay(
            f"### {LOGO} Merge Requests\n"
            f"Looking to merge with us? If you want to do bounty raids together or team merges, click below."
        ))
        r2 = discord.ui.ActionRow()
        r2.add_item(discord.ui.Button(label="Merge", style=discord.ButtonStyle.secondary, custom_id="ticket_merge"))
        cont.add_item(r2)

        cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        # SUPPORT - With blue ticket
        cont.add_item(discord.ui.TextDisplay(
            f"### {BLUE_TICKET} Support Center\n"
            f"Response times are usually faster during the day. They can be longer during busy periods due to high demand — please be patient."
        ))
        r3 = discord.ui.ActionRow()
        r3.add_item(discord.ui.Button(label="Support", style=discord.ButtonStyle.secondary, custom_id="ticket_support"))
        cont.add_item(r3)

        cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        # All rights reserved - NO EMOJIS as requested
        cont.add_item(discord.ui.TextDisplay(f"-# GREEKS NETWORK • All rights reserved"))

        self.add_item(cont)

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tickets = {}

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.bot.add_view(TopPanelView())
        except:
            pass

    @app_commands.command(name="setup_tickets", description="Setup OLA")
    @app_commands.describe(panel_channel="Panel", logs_channel="Logs", transcript_channel="Transcripts", category="Category", role1="Role1", role2="Role2", role3="Role3")
    async def setup_tickets(self, interaction: discord.Interaction, panel_channel: discord.TextChannel = None, logs_channel: discord.TextChannel = None, transcript_channel: discord.TextChannel = None, category: discord.CategoryChannel = None, role1: discord.Role = None, role2: discord.Role = None, role3: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        if logs_channel: cfg["channels"]["ticket_logs"] = logs_channel.id
        if transcript_channel: cfg["channels"]["transcript"] = transcript_channel.id
        if category: cfg["channels"]["category"] = category.id
        if role1:
            r = [role1.id]
            if role2: r.append(role2.id)
            if role3: r.append(role3.id)
            cfg["roles"]["ticket_roles"] = r
        save_config(cfg)
        await (panel_channel or interaction.channel).send(view=TopPanelView())
        await interaction.followup.send("Setup done!", ephemeral=True)

    @app_commands.command(name="resync", description="Force sync")
    async def resync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced = await self.bot.tree.sync(guild=interaction.guild)
        await interaction.followup.send(f"Synced {len(synced)}!", ephemeral=True)

    async def create_ticket(self, interaction: discord.Interaction, category: str, issue: str):
        g = interaction.guild
        u = interaction.user
        cfg = load_config()
        overwrites = {
            g.default_role: discord.PermissionOverwrite(view_channel=False),
            u: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
            g.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        for rid in cfg.get("roles", {}).get("ticket_roles", []):
            role = g.get_role(rid)
            if role: overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        parent = g.get_channel(cfg.get("channels", {}).get("category")) if cfg.get("channels", {}).get("category") else None
        ch = await g.create_text_channel(name=f"ticket-{u.name.lower()}-{category.lower()}", overwrites=overwrites, category=parent)
        self.tickets[ch.id] = {"cat": category, "issue": issue, "creator_id": u.id, "creator_name": str(u), "created_at": datetime.now(), "claimed_by": None}
        ts = int(datetime.now().timestamp())
        
        view = discord.ui.LayoutView(timeout=None)
        cont = discord.ui.Container()
        cont.add_item(discord.ui.TextDisplay(f"## {BLUE_TICKET} {category} Ticket"))
        cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        cont.add_item(discord.ui.TextDisplay(f"**User:** {u.mention} • `{u.id}`\n**Category:** `{category}` • <t:{ts}:F>"))
        cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        cont.add_item(discord.ui.TextDisplay(f"**Issue:**\n```{issue[:1000]}```"))
        cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        row = discord.ui.ActionRow()
        row.add_item(discord.ui.Button(label="Claim", style=discord.ButtonStyle.secondary, custom_id="tc_claim"))
        row.add_item(discord.ui.Button(label="Ping", style=discord.ButtonStyle.secondary, custom_id="tc_ping_member"))
        row.add_item(discord.ui.Button(label="Close", style=discord.ButtonStyle.danger, custom_id="tc_close"))
        cont.add_item(row)
        cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        cont.add_item(discord.ui.TextDisplay(f"-# {LOGO} GREEKS NETWORK"))
        view.add_item(cont)
        
        await ch.send(view=view)
        await interaction.followup.send(f"Ticket: {ch.mention} {BLUE_TICKET}", ephemeral=True)
        
        log_id = cfg.get("channels", {}).get("ticket_logs")
        if log_id:
            log_ch = g.get_channel(log_id)
            if log_ch:
                lv = discord.ui.LayoutView(timeout=None)
                lc = discord.ui.Container()
                lc.add_item(discord.ui.TextDisplay(f"## {BLUE_TICKET} {category} Opened"))
                lc.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                lc.add_item(discord.ui.TextDisplay(f"**User:** {u.mention} • `{u.id}`\n**Channel:** {ch.mention}\n**Category:** `{category}` • <t:{ts}:F>"))
                lc.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                lc.add_item(discord.ui.TextDisplay(f"**Issue:**\n```{issue[:1000]}```"))
                lc.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                lc.add_item(discord.ui.TextDisplay(f"-# {LOGO} Logs"))
                lv.add_item(lc)
                await log_ch.send(view=lv)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        cid = interaction.data["custom_id"]
        if cid in ["ticket_team", "ticket_merge", "ticket_support"]:
            await interaction.response.send_modal(IssueModal(cid.split("_")[1].capitalize()))
        elif cid == "tc_claim":
            await interaction.response.defer()
            if interaction.channel.id in self.tickets:
                self.tickets[interaction.channel.id]["claimed_by"] = interaction.user.id
            v = discord.ui.LayoutView(timeout=None)
            c = discord.ui.Container()
            c.add_item(discord.ui.TextDisplay(f"### {BLUE_TICKET} Claimed by {interaction.user.mention}"))
            v.add_item(c)
            await interaction.followup.send(view=v)
        elif cid == "tc_ping_member":
            await interaction.response.send_modal(PingMemberModal(interaction.channel.id))
        elif cid == "tc_close":
            await interaction.response.defer()
            channel = interaction.channel
            data = self.tickets.get(channel.id, {})
            msgs = []
            async for m in channel.history(limit=None, oldest_first=True):
                if m.content:
                    msgs.append(f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.author} ({m.author.id}): {m.content}")
            text = "\n".join(msgs) if msgs else "No messages"
            file_transcript = discord.File(io.BytesIO(text.encode()), filename=f"transcript-{channel.name}.txt")
            file_transcript_log = discord.File(io.BytesIO(text.encode()), filename=f"transcript-{channel.name}.txt")
            creator_id = data.get('creator_id', 'Unknown')
            creator_mention = f"<@{creator_id}>" if isinstance(creator_id, int) else f"`{creator_id}`"
            cat = data.get('cat', 'Unknown')
            issue = data.get('issue', 'No issue')
            created_at = data.get('created_at')
            created_ts = int(created_at.timestamp()) if created_at else int(datetime.now().timestamp())
            claimed = data.get('claimed_by')
            claimed_text = f"<@{claimed}> | `{claimed}`" if claimed else "`Not claimed`"
            close_ts = int(datetime.now().timestamp())
            cfg = load_config()
            tid = cfg.get("channels", {}).get("transcript")
            if tid:
                ch = interaction.guild.get_channel(tid)
                if ch:
                    await ch.send(content=f"Transcript `{channel.name}` - <t:{close_ts}:F> {BLUE_TICKET}", file=file_transcript)
            lid = cfg.get("channels", {}).get("ticket_logs")
            if lid:
                ch = interaction.guild.get_channel(lid)
                if ch:
                    log_view = discord.ui.LayoutView(timeout=None)
                    log_cont = discord.ui.Container()
                    log_cont.add_item(discord.ui.TextDisplay(f"## {BLUE_TICKET} {cat} Closed {LOGO}"))
                    log_cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_cont.add_item(discord.ui.TextDisplay(
                        f"**Channel:** `{channel.name}`\n"
                        f"**Category:** `{cat}`\n"
                        f"**By:** {creator_mention}\n"
                        f"**Created:** <t:{created_ts}:F>\n"
                        f"**Closed By:** {interaction.user.mention}\n"
                        f"**Claimed:** {claimed_text}\n"
                        f"**Messages:** `{len(msgs)}`"
                    ))
                    log_cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_cont.add_item(discord.ui.TextDisplay(f"**Issue:**\n```{issue[:1000]}```"))
                    log_cont.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_cont.add_item(discord.ui.TextDisplay(f"-# {LOGO} Closed"))
                    log_view.add_item(log_cont)
                    await ch.send(view=log_view, file=file_transcript_log)
            await channel.delete()

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))