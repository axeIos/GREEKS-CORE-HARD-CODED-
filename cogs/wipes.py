import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, date, time, timedelta
import calendar

CONFIG_PATH = "config.json"
GREEKS_LOGO = "<:GreeksLogo:1505682080330420244>"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"channels": {}, "roles": {}, "panel": {}}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

def get_last_thursday(year, month):
    last_day = calendar.monthrange(year, month)[1]
    for d in range(last_day, 0, -1):
        dt = date(year, month, d)
        if dt.weekday() == 3:
            return dt
    return None

def get_next_clan_wipe():
    now = datetime.now()
    days_ahead = (4 - now.weekday()) % 7
    next_friday = now + timedelta(days=days_ahead)
    next_friday_10 = datetime.combine(next_friday.date(), time(10, 0))
    if next_friday_10 <= now:
        next_friday_10 += timedelta(days=7)
    return next_friday_10

def get_next_official_wipe():
    now = datetime.now()
    this_month_last = get_last_thursday(now.year, now.month)
    this_month_wipe = datetime.combine(this_month_last, time(21, 0))
    if this_month_wipe > now:
        return this_month_wipe
    next_month = now.month + 1
    next_year = now.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    next_last = get_last_thursday(next_year, next_month)
    next_wipe = datetime.combine(next_last, time(21, 0))
    return next_wipe

def format_countdown(target):
    now = datetime.now()
    diff = target - now
    days = diff.days
    hours = diff.seconds // 3600
    return f"{days}d {hours}h" if days > 0 else f"{hours}h"

def make_wipe_embed():
    now = datetime.now()
    clan_wipe = get_next_clan_wipe()
    official_wipe = get_next_official_wipe()
    clan_days = (clan_wipe.date() - now.date()).days
    official_days = (official_wipe.date() - now.date()).days
    embed = discord.Embed(
        title=f"{GREEKS_LOGO} WIPE SCHEDULE",
        description=(
            f"### CLAN SERVERS\nWipe: Every Friday at 10:00\nNext: {clan_wipe.strftime('%d/%m/%Y')} - In {clan_days} days\n\n"
            f"### OFFICIAL SERVERS\nWipe: Last Thursday at 21:00\nNext: {official_wipe.strftime('%d/%m/%Y')} - In {official_days} days\n\n"
            f"-# Auto updates | {now.strftime('%d/%m/%Y %H:%M')}"
        ),
    )
    embed.set_footer(text="GREEKS NETWORK | All rights reserved")
    return embed

class WipeView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        main = discord.ui.Container()
        now = datetime.now()
        clan_wipe = get_next_clan_wipe()
        official_wipe = get_next_official_wipe()
        clan_days = (clan_wipe.date() - now.date()).days
        official_days = (official_wipe.date() - now.date()).days
        main.add_item(discord.ui.TextDisplay(f"# {GREEKS_LOGO} WIPE SCHEDULE"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        main.add_item(discord.ui.TextDisplay(f"## CLAN SERVERS\nEvery Friday at 10:00\n### In {clan_days} days - {clan_wipe.strftime('%d/%m/%Y')}"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        main.add_item(discord.ui.TextDisplay(f"## OFFICIAL SERVERS\nLast Thursday at 21:00\n### In {official_days} days - {official_wipe.strftime('%d/%m/%Y')}"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        main.add_item(discord.ui.TextDisplay(f"-# Auto updates | {now.strftime('%d/%m/%Y')}"))
        self.add_item(main)

class WipeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()
    def cog_unload(self):
        self.update_loop.cancel()
    @tasks.loop(hours=1)
    async def update_loop(self):
        await self.bot.wait_until_ready()
        cfg = load_config()
        ch_id = cfg.get("panel", {}).get("wipe_channel")
        msg_id = cfg.get("panel", {}).get("wipe_message")
        if not ch_id or not msg_id:
            return
        try:
            ch = self.bot.get_channel(ch_id)
            msg = await ch.fetch_message(msg_id)
            await msg.edit(view=WipeView())
        except:
            pass
    @update_loop.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()
    @app_commands.command(name="setup_wipes", description="Setup wipe panel")
    @app_commands.default_permissions(administrator=True)
    async def setup_wipes(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel
        msg = await target.send(view=WipeView())
        cfg = load_config()
        if "panel" not in cfg:
            cfg["panel"] = {}
        cfg["panel"]["wipe_channel"] = target.id
        cfg["panel"]["wipe_message"] = msg.id
        save_config(cfg)
        await interaction.followup.send(f"Wipe setup {GREEKS_LOGO}", ephemeral=True)
    @app_commands.command(name="wipes", description="Check wipes")
    async def wipes_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=make_wipe_embed(), ephemeral=True)
    @commands.command(name="wipes")
    async def wipes_prefix(self, ctx):
        await ctx.send(embed=make_wipe_embed())

async def setup(bot):
    await bot.add_cog(WipeCog(bot))