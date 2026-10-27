import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import LayoutView, Container, TextDisplay, Separator

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say", description="Make the bot say something (Admin only)")
    @app_commands.describe(message="Text to send", channel="Target channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def say(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
        target = channel or interaction.channel
        await target.send(message)
        await interaction.response.send_message(f"✅ Sent in {target.mention}", ephemeral=True)

    @app_commands.command(name="say_embed", description="Send a Components V2 message (Admin only)")
    @app_commands.describe(
        title="Title",
        description="Content",
        color="Hex color e.g. #5865F2",
        channel="Target channel",
        image_url="Optional image url"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def say_embed(
        self, interaction: discord.Interaction,
        title: str,
        description: str,
        color: str = "#5865F2",
        channel: discord.TextChannel = None,
        image_url: str = None
    ):
        target = channel or interaction.channel

        try:
            accent = int(color.replace("#", "").strip(), 16)
        except:
            accent = 0x5865F2

        # Components V2 - fixed for 2.6.4
        layout = LayoutView()
        container = Container(accent_color=accent)

        container.add_item(TextDisplay(content=f"## {title}"))
        container.add_item(Separator())  # no spacing arg needed in 2.6.4
        container.add_item(TextDisplay(content=description))

        layout.add_item(container)
        
        await target.send(view=layout)

        if image_url:
            em = discord.Embed(color=accent)
            em.set_image(url=image_url)
            await target.send(embed=em)

        await interaction.response.send_message(f"✅ V2 Embed sent in {target.mention}", ephemeral=True)

    @say.error
    @say_embed.error
    async def on_admin_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ You need `Administrator` permission.", ephemeral=True)
        else:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Say(bot))