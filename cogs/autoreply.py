import discord
from discord.ext import commands
from discord import app_commands
import json, pathlib as pl, datetime

DATA_FILE = pl.Path("data/vip_list.json")

DEFAULT_DATA = {
    "names_channel": None,
    "list_channel": None,
    "list_message_id": None,
    "names": [],  # [{"user_id": 123, "name": "xxx"}]
    "active": False
}

VIP_EMOJI = "<:vip_vip:1561452199169761352>"

def load_data():
    if not DATA_FILE.exists():
        return DEFAULT_DATA.copy()
    try:
        data = json.loads(DATA_FILE.read_text())
        for k,v in DEFAULT_DATA.items():
            if k not in data:
                data[k]=v
        return data
    except:
        return DEFAULT_DATA.copy()

def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def build_vip_list_view(data):
    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container()

    names = data.get("names", [])
    active = data.get("active", False)
    status = "🟢 ACTIVE" if active else "🔴 STOPPED"

    container.add_item(discord.ui.TextDisplay(f"## {VIP_EMOJI} VIP LIST"))
    container.add_item(discord.ui.TextDisplay(f"**Status:** {status} | **Total:** {len(names)}"))
    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

    if not names:
        container.add_item(discord.ui.TextDisplay(f"**List is empty**\n-# Send your name in <#{data.get('names_channel')}>"))
    else:
        # Copy-paste friendly format: Vipid "name"
        lines = []
        for entry in names:
            name = entry.get("name", "").strip()
            # escape quotes
            safe_name = name.replace('"', "'")
            lines.append(f'Vipid "{safe_name}"')
        
        text = "\n".join(lines)
        if len(text) > 3800:
            text = text[:3800] + "\n... truncated"

        container.add_item(discord.ui.TextDisplay(f"```\n{text}\n```"))

    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(discord.ui.TextDisplay(f"-# Last update: <t:{int(utc_now().timestamp())}:R> | One per user"))

    view.add_item(container)
    return view

class VipListCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_list_message(self):
        data = load_data()
        list_ch_id = data.get("list_channel")
        if not list_ch_id:
            return

        list_ch = None
        for g in self.bot.guilds:
            ch = g.get_channel(list_ch_id)
            if ch:
                list_ch = ch
                break
        if not list_ch:
            try:
                list_ch = await self.bot.fetch_channel(list_ch_id)
            except:
                return

        view = build_vip_list_view(data)
        msg_id = data.get("list_message_id")

        try:
            if msg_id:
                try:
                    msg = await list_ch.fetch_message(msg_id)
                    await msg.edit(view=view)
                    return
                except:
                    pass
            msg = await list_ch.send(view=view)
            data["list_message_id"] = msg.id
            save_data(data)
        except Exception as e:
            print(f"VIP update error: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        data = load_data()
        if not data.get("active"):
            return
        
        names_ch_id = data.get("names_channel")
        if not names_ch_id or message.channel.id != names_ch_id:
            return

        content = message.content.strip()
        if not content or len(content) < 2 or len(content) > 40:
            return

        # One per user
        for entry in data.get("names", []):
            if entry.get("user_id") == message.author.id:
                try:
                    await message.delete()
                except:
                    pass
                return

        data["names"].append({
            "user_id": message.author.id,
            "name": content,
            "username": str(message.author)
        })
        save_data(data)

        try:
            await message.delete()
        except:
            pass

        await self.update_list_message()

    @app_commands.command(name="setup_vip", description="Setup VIP list system")
    @app_commands.default_permissions(administrator=True)
    async def setup_vip(self, interaction: discord.Interaction, names_channel: discord.TextChannel, list_channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        data["names_channel"] = names_channel.id
        data["list_channel"] = list_channel.id
        data["active"] = False
        save_data(data)

        view = build_vip_list_view(data)
        try:
            msg = await list_channel.send(view=view)
            data["list_message_id"] = msg.id
            save_data(data)
        except Exception as e:
            await interaction.followup.send(f"Setup error: {e}", ephemeral=True)
            return

        await interaction.followup.send(f"✅ Setup done\nNames: {names_channel.mention}\nList: {list_channel.mention}\nUse `/vip_start`", ephemeral=True)

    @app_commands.command(name="vip_start", description="Start VIP collection")
    @app_commands.default_permissions(administrator=True)
    async def vip_start(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        if not data.get("names_channel"):
            await interaction.followup.send("❌ Run /setup_vip first", ephemeral=True)
            return
        data["active"] = True
        save_data(data)
        await self.update_list_message()
        await interaction.followup.send(f"🟢 STARTED {VIP_EMOJI}", ephemeral=True)

    @app_commands.command(name="vip_stop", description="Stop VIP collection")
    @app_commands.default_permissions(administrator=True)
    async def vip_stop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        data["active"] = False
        save_data(data)
        await self.update_list_message()
        await interaction.followup.send(f"🔴 STOPPED {VIP_EMOJI}", ephemeral=True)

    @app_commands.command(name="vip_reset", description="Reset VIP list")
    @app_commands.default_permissions(administrator=True)
    async def vip_reset(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        data["names"] = []
        save_data(data)
        await self.update_list_message()
        await interaction.followup.send(f"✅ RESET {VIP_EMOJI}", ephemeral=True)

    @app_commands.command(name="vip_remove", description="Remove user from VIP list")
    @app_commands.default_permissions(administrator=True)
    async def vip_remove(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        before = len(data["names"])
        data["names"] = [n for n in data["names"] if n.get("user_id") != user.id]
        save_data(data)
        if len(data["names"]) < before:
            await self.update_list_message()
            await interaction.followup.send(f"✅ Removed {user.mention}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Not in list", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VipListCog(bot))