import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os

CONFIG_PATH = "config.json"
BANNER_URL = "https://cdn.discordapp.com/attachments/1551421560215179367/1555275940056268861/giphy.gif"
TIKTOK_URL = "https://www.tiktok.com/@greeks.rce"
VAULTCORD_URL = "https://vaultcord.win/greeksnetwork?a4c298ed4be3d0fb"

NAKED_EMOJI = "<:Naked:1498372975278428341>"
GREEKS_LOGO = "<:GreeksLogo:1505682080330420244>"
TIKTOK_EMOJI = "<:15188tiktok:1555491659389607947>"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"channels": {}, "roles": {"verification_role": None, "trial_role": None, "team_role": None}, "panel": {}}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

def get_role_counts(guild, cfg):
    trial = 0
    team = 0
    try:
        tid = cfg.get("roles", {}).get("trial_role")
        team_id = cfg.get("roles", {}).get("team_role")
        if tid and guild.get_role(tid):
            trial = len(guild.get_role(tid).members)
        if team_id and guild.get_role(team_id):
            team = len(guild.get_role(team_id).members)
    except:
        pass
    return trial, team

class VerificationView(discord.ui.LayoutView):
    def __init__(self, guild=None, cfg=None):
        super().__init__(timeout=None)
        if cfg is None:
            cfg = load_config()
        trial, team = get_role_counts(guild, cfg) if guild else (0, 0)
        main = discord.ui.Container()
        try:
            g = discord.ui.MediaGallery()
            g.add_item(media=BANNER_URL)
            main.add_item(g)
            main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        except:
            pass
        main.add_item(discord.ui.TextDisplay(f"# {GREEKS_LOGO} GREEKS NETWORK"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        try:
            tiktok_emoji = discord.PartialEmoji.from_str(TIKTOK_EMOJI)
            tiktok_btn = discord.ui.Button(label="TikTok", style=discord.ButtonStyle.link, url=TIKTOK_URL, emoji=tiktok_emoji)
        except:
            tiktok_btn = discord.ui.Button(label="TikTok", style=discord.ButtonStyle.link, url=TIKTOK_URL)
        about_section = discord.ui.Section(
            discord.ui.TextDisplay(f"## About Us\nElite Rust team focused on teamwork, raiding and wipes.\nConsole & PC Support - All region times."),
            accessory=tiktok_btn
        )
        main.add_item(about_section)
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        main.add_item(discord.ui.TextDisplay(f"## Why Verify?"))
        main.add_item(discord.ui.TextDisplay(f"• Access to Applications - main roster / tryouts\n• Console & PC - Rust Console and Steam\n• Base Loot and Raids - codes, loot share"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        main.add_item(discord.ui.TextDisplay(f"## {GREEKS_LOGO} Live Team Stats"))
        main.add_item(discord.ui.TextDisplay(f"```\nTrial: {trial}\nTeam: {team}\n```"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        main.add_item(discord.ui.TextDisplay(f"## How to Verify"))
        main.add_item(discord.ui.TextDisplay(f"**1.** Click the Verify button below\n**2.** Read the rules before you verify"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        r1 = discord.ui.ActionRow()
        try:
            e1 = discord.PartialEmoji.from_str(NAKED_EMOJI)
            r1.add_item(discord.ui.Button(label="Verify", style=discord.ButtonStyle.link, url=VAULTCORD_URL, emoji=e1))
        except:
            r1.add_item(discord.ui.Button(label="Verify", style=discord.ButtonStyle.link, url=VAULTCORD_URL))
        main.add_item(r1)
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        main.add_item(discord.ui.TextDisplay(f"-# GREEKS NETWORK | All rights reserved"))
        self.add_item(main)

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.live_update_loop.start()
    def cog_unload(self):
        self.live_update_loop.cancel()
    @tasks.loop(minutes=2)
    async def live_update_loop(self):
        cfg = load_config()
        panel = cfg.get("panel", {})
        if not panel.get("channel_id") or not panel.get("message_id"):
            return
        try:
            for guild in self.bot.guilds:
                if guild.id != panel.get("guild_id"):
                    continue
                channel = guild.get_channel(panel["channel_id"])
                if not channel:
                    continue
                try:
                    msg = await channel.fetch_message(panel["message_id"])
                    new_view = VerificationView(guild=guild, cfg=cfg)
                    await msg.edit(view=new_view)
                except:
                    pass
        except:
            pass
    @live_update_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.bot.add_view(VerificationView())
        except:
            pass
    @app_commands.command(name="setup_verification", description="Setup verification")
    @app_commands.describe(channel="Channel", verification_role="Role", trial_role="Trial", team_role="Team", logs_channel="Logs")
    @app_commands.default_permissions(administrator=True)
    async def setup_verification(self, interaction: discord.Interaction, channel: discord.TextChannel = None, verification_role: discord.Role = None, trial_role: discord.Role = None, team_role: discord.Role = None, logs_channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        if "roles" not in cfg:
            cfg["roles"] = {}
        if "channels" not in cfg:
            cfg["channels"] = {}
        if "panel" not in cfg:
            cfg["panel"] = {}
        if verification_role:
            cfg["roles"]["verification_role"] = verification_role.id
        if trial_role:
            cfg["roles"]["trial_role"] = trial_role.id
        if team_role:
            cfg["roles"]["team_role"] = team_role.id
        if logs_channel:
            cfg["channels"]["verification_logs"] = logs_channel.id
        target = channel or interaction.channel
        view = VerificationView(guild=interaction.guild, cfg=cfg)
        msg = await target.send(view=view)
        cfg["panel"]["channel_id"] = target.id
        cfg["panel"]["message_id"] = msg.id
        cfg["panel"]["guild_id"] = interaction.guild.id
        save_config(cfg)
        await interaction.followup.send(f"Panel sent + Live update every 2min ON {GREEKS_LOGO}", ephemeral=True)
    @app_commands.command(name="panel_verification", description="Resend panel")
    @app_commands.default_permissions(administrator=True)
    async def panel_verification(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        if "panel" not in cfg:
            cfg["panel"] = {}
        target = channel or interaction.channel
        view = VerificationView(guild=interaction.guild, cfg=cfg)
        msg = await target.send(view=view)
        cfg["panel"]["channel_id"] = target.id
        cfg["panel"]["message_id"] = msg.id
        cfg["panel"]["guild_id"] = interaction.guild.id
        save_config(cfg)
        await interaction.followup.send(f"Panel resent + Live 2min ON {GREEKS_LOGO}", ephemeral=True)
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or interaction.data.get("custom_id") != "verify_custom":
            return
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        guild = interaction.guild
        rid = cfg.get("roles", {}).get("verification_role")
        role = guild.get_role(rid) if rid else None
        if not role:
            for r in guild.roles:
                if r.name.lower() == "naked":
                    role = r
                    break
        if not role:
            await interaction.followup.send(f"Role not found!", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.followup.send(f"Already verified {NAKED_EMOJI}", ephemeral=True)
            return
        try:
            await interaction.user.add_roles(role, reason="Verification")
            await interaction.followup.send(f"Verified {NAKED_EMOJI} {role.mention}", ephemeral=True)
            panel = cfg.get("panel", {})
            if panel.get("channel_id") and panel.get("message_id"):
                try:
                    ch = guild.get_channel(panel["channel_id"])
                    if ch:
                        m = await ch.fetch_message(panel["message_id"])
                        new_view = VerificationView(guild=guild, cfg=cfg)
                        await m.edit(view=new_view)
                except:
                    pass
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))