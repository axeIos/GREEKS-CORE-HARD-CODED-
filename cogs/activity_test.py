import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime, typing
from utils.helpers import load_config, save_config

LOGO = "<:GreeksLogo:1505682080330420244>"

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def build_view(tid, question, wipe_time, end, votes, ended=False):
    if end.tzinfo is None:
        end = end.replace(tzinfo=datetime.timezone.utc)

    real_total = sum(len(v) for v in votes.values())
    total = real_total or 1

    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container()

    title = f"{LOGO} GREEKS NETWORK - ACTIVITY TEST - ENDED" if ended else f"{LOGO} GREEKS NETWORK - ACTIVITY TEST"

    container.add_item(discord.ui.TextDisplay(
        f"## {title}\n"
        f"### {question}\n"
        f"Wipe: **{wipe_time}** | Ends: <t:{int(end.timestamp())}:R> | Total: **{real_total}**"
    ))
    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

    for label, key in [("On Time", "on_time"), ("Later", "later"), ("No", "no")]:
        count = len(votes.get(key, []))
        pct = (count / total * 100) if real_total else 0
        bar = "█" * int(pct/8) + "░" * (12 - int(pct/8))
        users = votes.get(key, [])
        names = "\n".join([f"- <@{uid}>" for uid in users[:12]]) if users else "`- No one yet`"
        if len(users) > 12:
            names += f"\n- +{len(users)-12} more"

        container.add_item(discord.ui.TextDisplay(
            f"### {LOGO} {label} `{bar}` {pct:.0f}% - {count}\n{names}"
        ))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

    if not ended:
        row1 = discord.ui.ActionRow()
        row1.add_item(discord.ui.Button(label="On Time", style=discord.ButtonStyle.success, custom_id=f"act_on_time_{tid}"))
        row1.add_item(discord.ui.Button(label="Later", style=discord.ButtonStyle.primary, custom_id=f"act_later_{tid}"))
        row1.add_item(discord.ui.Button(label="No", style=discord.ButtonStyle.danger, custom_id=f"act_no_{tid}"))
        container.add_item(row1)

        row2 = discord.ui.ActionRow()
        row2.add_item(discord.ui.Button(label="End Now (Admin)", style=discord.ButtonStyle.secondary, custom_id=f"act_end_{tid}"))
        container.add_item(row2)

    container.add_item(discord.ui.TextDisplay(
        f"-# {LOGO} GREEKS NETWORK | <t:{int(end.timestamp())}:F> | Auto updates"
    ))

    view.add_item(container)
    return view

class ActivityTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @app_commands.command(name="activity_test", description="Create wipe activity test - GREEKS NETWORK")
    @app_commands.default_permissions(administrator=True)
    async def activity_test(self, interaction: discord.Interaction, question: str = "Will you be there for wipe?", duration: int = 720, channel: typing.Optional[discord.TextChannel] = None, ping_role: typing.Optional[discord.Role] = None, wipe_time: str = "20:00 EU"):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel
        end = utc_now() + datetime.timedelta(minutes=duration)

        cfg = load_config()
        if "activity_tests" not in cfg:
            cfg["activity_tests"] = {}
        tid = str(interaction.id)
        cfg["activity_tests"][tid] = {
            "question": question,
            "wipe_time": wipe_time,
            "end_time": end.isoformat(),
            "channel_id": target.id,
            "message_id": None,
            "votes": {"on_time": [], "later": [], "no": []},
            "created_by": interaction.user.id,
            "ended": False
        }
        save_config(cfg)

        view = build_view(tid, question, wipe_time, end, {"on_time": [], "later": [], "no": []}, False)
        msg = await target.send(content=ping_role.mention if ping_role else None, view=view)

        cfg["activity_tests"][tid]["message_id"] = msg.id
        save_config(cfg)

        await interaction.followup.send(f"Created in {target.mention} {LOGO} GREEKS NETWORK", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return
        cid = interaction.data["custom_id"]
        if not cid.startswith("act_"):
            return

        # IMPORTANT: ephemeral defer so no thinking visible to everyone
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=False)
        except:
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=True)
            except:
                pass

        cfg = load_config()

        if cid.startswith("act_end_"):
            tid = cid.replace("act_end_", "")
            t = cfg.get("activity_tests", {}).get(tid)
            if not t:
                return
            if not interaction.user.guild_permissions.administrator:
                try:
                    await interaction.followup.send("Only admins - GREEKS NETWORK", ephemeral=True)
                except:
                    pass
                return

            t["ended"] = True
            cfg["activity_tests"][tid] = t
            save_config(cfg)

            end = datetime.datetime.fromisoformat(t["end_time"])
            view = build_view(tid, t["question"], t["wipe_time"], end, t["votes"], True)
            try:
                ch = self.bot.get_channel(t["channel_id"]) or await self.bot.fetch_channel(t["channel_id"])
                msg = await ch.fetch_message(t["message_id"])
                await msg.edit(view=view)
                await interaction.followup.send(f"Ended {LOGO} GREEKS NETWORK", ephemeral=True)
            except Exception as e:
                print(f"End error: {e}")
                try:
                    await interaction.followup.send(f"Ended but edit failed: {e}", ephemeral=True)
                except:
                    pass
            return

        key = None
        tid = None
        if cid.startswith("act_on_time_"):
            key, tid = "on_time", cid.replace("act_on_time_", "")
        elif cid.startswith("act_later_"):
            key, tid = "later", cid.replace("act_later_", "")
        elif cid.startswith("act_no_"):
            key, tid = "no", cid.replace("act_no_", "")
        else:
            return

        t = cfg.get("activity_tests", {}).get(tid)
        if not t or t.get("ended"):
            try:
                await interaction.followup.send("This test has ended", ephemeral=True)
            except:
                pass
            return

        et = datetime.datetime.fromisoformat(t["end_time"])
        if et.tzinfo is None:
            et = et.replace(tzinfo=datetime.timezone.utc)

        if utc_now() >= et:
            t["ended"] = True
            cfg["activity_tests"][tid] = t
            save_config(cfg)
            view = build_view(tid, t["question"], t["wipe_time"], et, t["votes"], True)
            try:
                ch = self.bot.get_channel(t["channel_id"]) or await self.bot.fetch_channel(t["channel_id"])
                msg = await ch.fetch_message(t["message_id"])
                await msg.edit(view=view)
            except:
                pass
            return

        uid = interaction.user.id
        for k in t["votes"]:
            if uid in t["votes"][k]:
                t["votes"][k].remove(uid)
        if uid not in t["votes"][key]:
            t["votes"][key].append(uid)

        cfg["activity_tests"][tid] = t
        save_config(cfg)

        view = build_view(tid, t["question"], t["wipe_time"], et, t["votes"], False)

        try:
            ch = self.bot.get_channel(t["channel_id"]) or await self.bot.fetch_channel(t["channel_id"])
            msg = await ch.fetch_message(t["message_id"])
            await msg.edit(view=view)
            # Delete the ephemeral thinking message - no visible response
            try:
                await interaction.delete_original_response()
            except:
                pass
        except Exception as e:
            print(f"Edit error: {e}")

    @tasks.loop(seconds=60)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        cfg = load_config()
        now = utc_now()
        changed = False
        for tid, t in list(cfg.get("activity_tests", {}).items()):
            if t.get("ended"):
                continue
            try:
                et = datetime.datetime.fromisoformat(t["end_time"])
                if et.tzinfo is None:
                    et = et.replace(tzinfo=datetime.timezone.utc)
                if now >= et:
                    ch = self.bot.get_channel(t["channel_id"])
                    if not ch:
                        try:
                            ch = await self.bot.fetch_channel(t["channel_id"])
                        except:
                            continue
                    if ch:
                        try:
                            msg = await ch.fetch_message(t["message_id"])
                            view = build_view(tid, t["question"], t["wipe_time"], et, t["votes"], True)
                            await msg.edit(view=view)
                        except:
                            pass
                    t["ended"] = True
                    changed = True
            except Exception as e:
                print(f"check_loop error {e}")
                pass
        if changed:
            save_config(cfg)

    @check_loop.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(ActivityTestCog(bot))