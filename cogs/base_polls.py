import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import typing
from utils.helpers import load_config, save_config

EMOJI = "<:GreeksLogo:1505682080330420244>"
LOGO = EMOJI

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def build_view(pid, question, images, options, votes, end, ended=False):
    if end.tzinfo is None:
        end = end.replace(tzinfo=datetime.timezone.utc)

    real_total = sum(len(v) for v in votes.values())
    total = real_total or 1

    view = discord.ui.LayoutView(timeout=None)
    c = discord.ui.Container()

    status_text = "ENDED" if ended else "LIVE POLL"
    title = f"{EMOJI} GREEKS NETWORK - BASE POLL {status_text}"
    
    c.add_item(discord.ui.TextDisplay(
        f"## {title}\n### {question}\n-# Ends: <t:{int(end.timestamp())}:R> | Total Votes: `{real_total}` | ID: `{pid[:6]}`"
    ))
    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    for i in range(len(images)):
        key = f"opt_{i}"
        count = len(votes.get(key, []))
        pct = (count / total * 100) if real_total else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        users = votes.get(key, [])
        if users:
            names = ", ".join([f"<@{uid}>" for uid in users[:6]])
            if len(users) > 6:
                names = names + f" +{len(users)-6} more"
        else:
            names = "*No votes yet - be first!*"

        gallery = discord.ui.MediaGallery()
        try:
            gallery.add_item(media=images[i], description=f"{i+1}. {options[i]}")
        except:
            gallery.add_item(discord.ui.MediaGalleryItem(media=images[i], description=f"{i+1}. {options[i]}"))
        c.add_item(gallery)

        c.add_item(discord.ui.TextDisplay(
            f"### {EMOJI} {i+1}. {options[i]} - `{count} votes`\n`{bar}` **{pct:.0f}%**\n{names}"
        ))

        if not ended:
            row = discord.ui.ActionRow()
            row.add_item(discord.ui.Button(
                label=f"Vote Base {i+1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"basepoll_{i}_{pid}",
                emoji="<:GreeksLogo:1505682080330420244>"
            ))
            c.add_item(row)

        if i < len(images) - 1:
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        else:
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

    if not ended:
        row_end = discord.ui.ActionRow()
        row_end.add_item(discord.ui.Button(
            label="End Poll (Admin)",
            style=discord.ButtonStyle.danger,
            custom_id=f"basepoll_end_{pid}",
            emoji="<:GreeksLogo:1505682080330420244>"
        ))
        c.add_item(row_end)
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    c.add_item(discord.ui.TextDisplay(f"-# {EMOJI} GREEKS NETWORK | Base Poll ends <t:{int(end.timestamp())}:F>"))
    view.add_item(c)
    return view

class BasePollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @app_commands.command(name="base_poll", description="Create a beautiful base poll for GREEKS NETWORK")
    @app_commands.describe(
        question="Poll question (e.g. Which base we build?)",
        image1="First base image",
        image2="Second base image",
        image3="Third base image (optional)",
        image4="Fourth base image (optional)",
        image5="Fifth base image (optional)",
        option1="Name for base 1",
        option2="Name for base 2",
        option3="Name for base 3",
        option4="Name for base 4",
        option5="Name for base 5",
        duration="Duration in minutes (default 1440 = 24h)",
        channel="Channel to send poll",
        ping_role="Role to ping"
    )
    @app_commands.default_permissions(administrator=True)
    async def base_poll(self, interaction: discord.Interaction, question: str, image1: discord.Attachment, image2: typing.Optional[discord.Attachment] = None, image3: typing.Optional[discord.Attachment] = None, image4: typing.Optional[discord.Attachment] = None, image5: typing.Optional[discord.Attachment] = None, option1: str = "Base 1", option2: str = "Base 2", option3: str = "Base 3", option4: str = "Base 4", option5: str = "Base 5", duration: int = 1440, channel: typing.Optional[discord.TextChannel] = None, ping_role: typing.Optional[discord.Role] = None):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel
        end = utc_now() + datetime.timedelta(minutes=duration)

        atts = [image1, image2, image3, image4, image5]
        opts = [option1, option2, option3, option4, option5]
        final_images = []
        final_options = []
        for idx, att in enumerate(atts):
            if att:
                final_images.append(att.url)
                final_options.append(opts[idx])

        if len(final_images) < 2:
            await interaction.followup.send("Vale toulaxiston 2 eikones!", ephemeral=True)
            return

        cfg = load_config()
        cfg.setdefault("base_polls", {})
        pid = str(interaction.id)
        cfg["base_polls"][pid] = {
            "question": question,
            "images": final_images,
            "options": final_options,
            "votes": {f"opt_{i}": [] for i in range(len(final_images))},
            "end_time": end.isoformat(),
            "channel_id": target.id,
            "message_id": None,
            "ended": False
        }
        save_config(cfg)

        view = build_view(pid, question, final_images, final_options, {f"opt_{i}": [] for i in range(len(final_images))}, end, False)
        msg = await target.send(content=ping_role.mention if ping_role else None, view=view)

        cfg["base_polls"][pid]["message_id"] = msg.id
        save_config(cfg)
        await interaction.followup.send(f"Created {EMOJI} **{len(final_images)} bases poll** in {target.mention}!", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return
        cid = interaction.data["custom_id"]
        if not cid.startswith("basepoll_"):
            return

        try:
            await interaction.response.defer()
        except:
            pass

        cfg = load_config()

        if cid.startswith("basepoll_end_"):
            pid = cid.replace("basepoll_end_", "")
            poll = cfg.get("base_polls", {}).get(pid)
            if not poll:
                return
            if not interaction.user.guild_permissions.administrator:
                try:
                    await interaction.followup.send("Only admins can end polls!", ephemeral=True)
                except:
                    pass
                return
            poll["ended"] = True
            cfg["base_polls"][pid] = poll
            save_config(cfg)
            end = datetime.datetime.fromisoformat(poll["end_time"])
            view = build_view(pid, poll["question"], poll["images"], poll["options"], poll["votes"], end, True)
            try:
                ch = self.bot.get_channel(poll["channel_id"])
                msg = await ch.fetch_message(poll["message_id"])
                await msg.edit(view=view)
                await interaction.followup.send(f"{EMOJI} Poll ended!", ephemeral=True)
            except:
                pass
            return

        try:
            parts = cid.split("_")
            idx = int(parts[1])
            pid = "_".join(parts[2:])
        except:
            return

        poll = cfg.get("base_polls", {}).get(pid)
        if not poll or poll.get("ended"):
            return

        et = datetime.datetime.fromisoformat(poll["end_time"])
        if et.tzinfo is None:
            et = et.replace(tzinfo=datetime.timezone.utc)
        if utc_now() >= et:
            poll["ended"] = True
            cfg["base_polls"][pid] = poll
            save_config(cfg)
            view = build_view(pid, poll["question"], poll["images"], poll["options"], poll["votes"], et, True)
            try:
                ch = self.bot.get_channel(poll["channel_id"])
                msg = await ch.fetch_message(poll["message_id"])
                await msg.edit(view=view)
            except:
                pass
            return

        uid = interaction.user.id
        key = f"opt_{idx}"
        for k in poll["votes"]:
            if uid in poll["votes"][k]:
                poll["votes"][k].remove(uid)
        if uid not in poll["votes"][key]:
            poll["votes"][key].append(uid)

        cfg["base_polls"][pid] = poll
        save_config(cfg)

        view = build_view(pid, poll["question"], poll["images"], poll["options"], poll["votes"], et, False)
        try:
            ch = self.bot.get_channel(poll["channel_id"])
            msg = await ch.fetch_message(poll["message_id"])
            await msg.edit(view=view)
        except Exception as e:
            print(f"Edit error: {e}")

    @tasks.loop(seconds=60)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        cfg = load_config()
        now = utc_now()
        changed = False
        for pid, poll in list(cfg.get("base_polls", {}).items()):
            if poll.get("ended"):
                continue
            try:
                et = datetime.datetime.fromisoformat(poll["end_time"])
                if et.tzinfo is None:
                    et = et.replace(tzinfo=datetime.timezone.utc)
                if now >= et:
                    ch = self.bot.get_channel(poll["channel_id"])
                    if ch:
                        try:
                            msg = await ch.fetch_message(poll["message_id"])
                            view = build_view(pid, poll["question"], poll["images"], poll["options"], poll["votes"], et, True)
                            await msg.edit(view=view)
                        except:
                            pass
                    poll["ended"] = True
                    changed = True
            except:
                pass
        if changed:
            save_config(cfg)

    @check_loop.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(BasePollCog(bot))