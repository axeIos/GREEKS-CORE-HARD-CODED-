import discord
from discord.ext import commands
from discord import app_commands
import json
import pathlib as pl
import datetime
import typing

DATA_FILE = pl.Path("data/reacts.json")

def load_data():
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text())
    except:
        return {}

def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))

def build_react_view(react_id: str, title: str, description: str, button_label: str, users: list, ping: bool = False):
    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container()

    try:
        greeks_emoji = discord.PartialEmoji(name="GreeksLogo", id=1505682080330420244)
    except:
        greeks_emoji = None

    # Ping INSIDE embed as first line
    if ping:
        container.add_item(discord.ui.TextDisplay(f"@everyone"))

    container.add_item(discord.ui.TextDisplay(f"## {title}"))
    if description:
        container.add_item(discord.ui.TextDisplay(description))

    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

    if not users:
        container.add_item(discord.ui.TextDisplay(f"**Reacted (0):**\n-# No one yet - press the button!"))
    else:
        mentions = [f"<@{uid}>" for uid in users]
        list_text = ", ".join(mentions)
        if len(list_text) > 900:
            list_text = list_text[:900] + f" +{len(users)} more"
        container.add_item(discord.ui.TextDisplay(f"**Reacted ({len(users)}):**\n{list_text}"))

    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(discord.ui.TextDisplay(f"-# Last update: <t:{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}:R>"))

    row = discord.ui.ActionRow()
    btn1 = discord.ui.Button(
        label=button_label[:80],
        style=discord.ButtonStyle.primary,
        custom_id=f"react_btn_{react_id}"
    )
    if greeks_emoji:
        btn1.emoji = greeks_emoji
    row.add_item(btn1)

    row.add_item(discord.ui.Button(
        label="Clear",
        style=discord.ButtonStyle.secondary,
        custom_id=f"react_clear_{react_id}"
    ))
    container.add_item(row)

    view.add_item(container)
    return view

class ReactCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return
        cid = interaction.data["custom_id"]

        if not cid.startswith("react_btn_") and not cid.startswith("react_clear_"):
            return

        try:
            parts = cid.split("_")
            action = parts[1]
            react_id = "_".join(parts[2:])

            data = load_data()
            if react_id not in data:
                if not interaction.response.is_done():
                    await interaction.response.send_message("This react message has expired", ephemeral=True)
                return

            entry = data[react_id]
            title = entry["title"]
            desc = entry["description"]
            btn_label = entry["button_label"]
            users = entry.get("users", [])
            owner_id = entry.get("owner_id")
            ping = entry.get("ping", False)

            if action == "btn":
                if interaction.user.id in users:
                    users.remove(interaction.user.id)
                else:
                    users.append(interaction.user.id)

                entry["users"] = users
                save_data(data)
                new_view = build_react_view(react_id, title, desc, btn_label, users, ping)
                await interaction.response.edit_message(view=new_view)

            elif action == "clear":
                is_mod = interaction.user.guild_permissions.manage_messages if interaction.guild else False
                if interaction.user.id != owner_id and not is_mod:
                    await interaction.response.send_message("Only the creator or mods can clear this", ephemeral=True)
                    return

                entry["users"] = []
                save_data(data)
                new_view = build_react_view(react_id, title, desc, btn_label, [], ping)
                await interaction.response.edit_message(view=new_view)

        except Exception as e:
            print(f"React error {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"Error: {e}", ephemeral=True)
            except:
                pass

    @app_commands.command(name="react", description="Create a react embed with button")
    @app_commands.describe(
        title="Top text (e.g. React test - I'm here)",
        description="Bottom description (optional)",
        button_label="Button label (e.g. I'm here)",
        channel="Channel to send it to (default: current)",
        ping="Ping @everyone inside the embed? (default: True)"
    )
    async def react_command(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str = "",
        button_label: str = "I'm here",
        channel: typing.Optional[discord.TextChannel] = None,
        ping: bool = True
    ):
        await interaction.response.defer(ephemeral=True)

        react_id = f"{interaction.user.id}{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"

        data = load_data()
        data[react_id] = {
            "title": title,
            "description": description,
            "button_label": button_label,
            "users": [],
            "owner_id": interaction.user.id,
            "ping": ping,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        save_data(data)

        view = build_react_view(react_id, title, description, button_label, [], ping)
        target = channel or interaction.channel

        try:
            # FIX: Ping INSIDE embed via TextDisplay, not content field
            # This avoids "content cannot be used with IS_COMPONENTS_V2" error
            # and puts @everyone inside the embed
            await target.send(view=view, allowed_mentions=discord.AllowedMentions(everyone=True))
            await interaction.followup.send(f"React created in {target.mention} | ID: `{react_id}`", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    @app_commands.command(name="react_list", description="View all active react messages")
    @app_commands.default_permissions(manage_messages=True)
    async def react_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        if not data:
            await interaction.followup.send("No active reacts found", ephemeral=True)
            return

        view = discord.ui.LayoutView(timeout=None)
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## Active Reacts ({len(data)})"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        txt = ""
        for rid, entry in list(data.items())[-10:]:
            txt += f"**{entry['title'][:30]}** - ID: `{rid}` - {len(entry.get('users',[]))} reacted\n"

        c.add_item(discord.ui.TextDisplay(txt or "None"))
        view.add_item(c)
        await interaction.followup.send(view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReactCog(bot))