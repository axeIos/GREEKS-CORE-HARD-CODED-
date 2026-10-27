
import discord, json, pathlib
CONFIG_PATH = pathlib.Path("config.json")
def load_config():
    try: return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except: return {"channels":{},"roles":{},"settings":{}}
def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

LOGO = "<:GreeksLogo:1505682080330420244>"
ACCENT = 0x2B2D31
BLUE = discord.ButtonStyle.primary

def make_v2_ticket_panel():
    # EXACTLY like screenshot: Title, We are team..., Get in Touch, description, buttons, footer
    view = discord.ui.LayoutView()
    c = discord.ui.Container()
    c.add_item(discord.ui.TextDisplay(f"### {LOGO} GREEKS NETWORK - TICKETS"))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"We are team, we dont sell anything {LOGO}"))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"**Get in Touch**"))
    c.add_item(discord.ui.TextDisplay(f"To contact our support team, click below to open a ticket. Provide clear details."))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    row = discord.ui.ActionRow()
    row.add_item(discord.ui.Button(label="Team", style=BLUE, custom_id="ticket_team"))
    row.add_item(discord.ui.Button(label="Merge", style=BLUE, custom_id="ticket_merge"))
    row.add_item(discord.ui.Button(label="Support", style=BLUE, custom_id="ticket_support"))
    c.add_item(row)
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"-# {LOGO} Greeks, All Rights Reserved - Ticket Panel"))
    view.add_item(c)
    return view

def make_v2_verification_panel():
    view = discord.ui.LayoutView()
    c = discord.ui.Container()
    c.add_item(discord.ui.TextDisplay(f"# {LOGO} GREEKS VERIFICATION"))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"Welcome to **GREEKS Rust Network!**\nTo get access to all channels you must verify."))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"Press the button to receive Naked role and unlock the server."))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    row = discord.ui.ActionRow()
    row.add_item(discord.ui.Button(label="Get Naked", style=BLUE, custom_id="get_naked"))
    c.add_item(row)
    view.add_item(c)
    return view

def make_v2_applications_panel():
    view = discord.ui.LayoutView()
    c = discord.ui.Container()
    c.add_item(discord.ui.TextDisplay(f"# {LOGO} GREEKS NETWORK - APPLICATIONS"))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"Apply to join GREEKS Rust Network. Choose your division below."))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"**Rust Console Division**"))
    row1 = discord.ui.ActionRow()
    row1.add_item(discord.ui.Button(label="Apply Console", style=BLUE, custom_id="app_console"))
    c.add_item(row1)
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"**Rust PC Division**"))
    row2 = discord.ui.ActionRow()
    row2.add_item(discord.ui.Button(label="Apply PC", style=BLUE, custom_id="app_pc"))
    c.add_item(row2)
    view.add_item(c)
    return view

def make_v2_team_status_panel(guild, members_data, role_name="Team"):
    view = discord.ui.LayoutView()
    c = discord.ui.Container()
    online = sum(1 for x in members_data if x['online'])
    total = len(members_data)
    c.add_item(discord.ui.TextDisplay(f"# {LOGO} GREEKS {role_name.upper()} - TEAM STATUS"))
    c.add_item(discord.ui.Separator())
    c.add_item(discord.ui.TextDisplay(f"**Online:** {online} / {total}"))
    c.add_item(discord.ui.Separator())
    lines = [f"{'🟢' if m['online'] else '⚫'} {m['mention']}" for m in members_data[:25]]
    c.add_item(discord.ui.TextDisplay("\n".join(lines) or "No members in this role"))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"-# Updated <t:{int(discord.utils.utcnow().timestamp())}:R>"))
    view.add_item(c)
    return view

def make_v2_logs_embed(title, description, color=ACCENT):
    view = discord.ui.LayoutView()
    c = discord.ui.Container()
    c.add_item(discord.ui.TextDisplay(f"**{LOGO} {title}**"))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(description))
    view.add_item(c)
    return view

def make_v2_ticket_opened_panel(category, user):
    import datetime
    view = discord.ui.LayoutView()
    c = discord.ui.Container()
    c.add_item(discord.ui.TextDisplay(f"## {LOGO} GREEKS NETWORK - {category.upper()} TICKET"))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"Hello {user.mention},\nThank you for opening a ticket. Support team will be with you shortly.\nPlease describe your issue."))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    c.add_item(discord.ui.TextDisplay(f"**Category:** {category}\n**User:** {user.mention}"))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    row = discord.ui.ActionRow()
    row.add_item(discord.ui.Button(label="Claim", style=BLUE, custom_id="tc_claim"))
    row.add_item(discord.ui.Button(label="Ping", style=BLUE, custom_id="tc_ping"))
    row.add_item(discord.ui.Button(label="Add Member", style=BLUE, custom_id="tc_add"))
    row.add_item(discord.ui.Button(label="Close", style=BLUE, custom_id="tc_close"))
    c.add_item(row)
    view.add_item(c)
    return view
