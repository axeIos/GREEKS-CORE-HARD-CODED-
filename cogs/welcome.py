import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import load_config, save_config, make_v2_logs_embed, ACCENT

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot=bot

    @app_commands.command(name="welcome_setup", description="Setup welcome - simple with announcement & rules")
    @app_commands.describe(
        welcome_channel="Where welcome will be sent",
        announcement_channel="Announcements channel",
        rules_channel="Rules channel",
        verification_channel="Verification channel",
        member_role="Optional role to ping"
    )
    @app_commands.default_permissions(administrator=True)
    async def welcome_setup(self, interaction: discord.Interaction,
        welcome_channel: discord.TextChannel,
        announcement_channel: discord.TextChannel = None,
        rules_channel: discord.TextChannel = None,
        verification_channel: discord.TextChannel = None,
        member_role: discord.Role = None
    ):
        cfg=load_config()
        cfg["channels"]["welcome"]=welcome_channel.id
        if announcement_channel: cfg["channels"]["announcement"]=announcement_channel.id
        if rules_channel: cfg["channels"]["rules"]=rules_channel.id
        if verification_channel: cfg["channels"]["verification"]=verification_channel.id
        if member_role: cfg["roles"]["welcome_role"]=member_role.id
        # VGALAME TO IMAGE ENTELWS
        if "settings" in cfg and "welcome_image_url" in cfg["settings"]:
            del cfg["settings"]["welcome_image_url"]
        save_config(cfg)
        await interaction.response.send_message(view=make_v2_logs_embed("Welcome Setup Saved", f"Welcome: {welcome_channel.mention}\nAnnouncement: {announcement_channel.mention if announcement_channel else 'Not set'}\nRules: {rules_channel.mention if rules_channel else 'Not set'}\nVerify: {verification_channel.mention if verification_channel else 'Not set'}\n\n✅ Xwris eikona - mono embed"), ephemeral=True)
        await self.send_welcome(interaction.user, welcome_channel, preview=True)

    def build_welcome_view(self, member, guild, cfg):
        member_count = guild.member_count
        owner_id = guild.owner_id

        ann_id = cfg["channels"].get("announcement") or cfg["channels"].get("announcements")
        rules_id = cfg["channels"].get("rules")
        ver_id = cfg["channels"].get("verification")

        ann_mention = f"<#{ann_id}>" if ann_id else "# ANNOUNCEMENTS"
        rules_mention = f"<#{rules_id}>" if rules_id else "# RULES"
        ver_mention = f"<#{ver_id}>" if ver_id else "# VERIFICATION"

        view = discord.ui.LayoutView()

        # DEN VAZOUME KAMIA EIKONA - MONO TO CONTAINER
        c = discord.ui.Container(accent_color=ACCENT)

        c.add_item(discord.ui.TextDisplay(f"**SERVER INFO**"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**GREEKS NETWORK** · Competitive Community · Active 24/7\nMembers: **{member_count}**\nCreated: 14 February 2026\nOwner: <@{owner_id}>"))

        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**LINKS**"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"{ann_mention} - Announcements\n{rules_mention} - Rules\n{ver_mention} - Verify"))

        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**WELCOME TO GREEKS NETWORK**\nWelcome {member.mention} you are member **#{member_count}**\nThanks for joining **GREEKS NETWORK!**"))

        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**MEMBER COUNT**\n**{member_count}** members and growing!"))

        view.add_item(c)
        return view

    async def send_welcome(self, member, channel, preview=False):
        cfg=load_config()
        guild=channel.guild
        view = self.build_welcome_view(member, guild, cfg)
        # OXI IMAGE - MONO TO EMBED
        await channel.send(view=view)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg=load_config()
        ch_id=cfg["channels"].get("welcome")
        if not ch_id: return
        ch=member.guild.get_channel(ch_id)
        if not ch: return
        await self.send_welcome(member, ch)

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))