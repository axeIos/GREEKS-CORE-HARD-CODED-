import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import random
import typing
from utils.helpers import load_config, save_config

LOGO = "<:GreeksLogo:1505682080330420244>"

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def parse_time(s):
    try:
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except:
        return utc_now()

def make_bar(percent, length=12):
    filled = int(length * percent / 100)
    return "█" * filled + "░" * (length - filled)

def make_simple_log_view(title, desc):
    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container()
    container.add_item(discord.ui.TextDisplay(f"## {LOGO} {title}\n{desc}"))
    view.add_item(container)
    return view

class PollsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()
        self.check_polls.start()

    def cog_unload(self):
        self.check_giveaways.cancel()
        self.check_polls.cancel()

    # ================= POLL =================
    @app_commands.command(name="poll", description="Create poll")
    @app_commands.describe(
        question="Question", 
        option1="Option 1", 
        option2="Option 2", 
        option3="Option 3", 
        option4="Option 4", 
        option5="Option 5", 
        channel="Channel to send poll", 
        ping_role="Role to ping", 
        duration="Duration in minutes (0 = no end)"
    )
    @app_commands.default_permissions(administrator=True)
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, 
                   option3: typing.Optional[str] = None, option4: typing.Optional[str] = None, 
                   option5: typing.Optional[str] = None, 
                   channel: typing.Optional[discord.TextChannel] = None, 
                   ping_role: typing.Optional[discord.Role] = None, 
                   duration: int = 1440):
        
        # FIX: No thinking, instant ephemeral response
        target = channel or interaction.channel
        options = [o for o in [option1, option2, option3, option4, option5] if o]
        end_time = utc_now() + datetime.timedelta(minutes=duration) if duration > 0 else None
        
        cfg = load_config()
        if "polls" not in cfg: 
            cfg["polls"] = {}
        poll_id = str(interaction.id)
        cfg["polls"][poll_id] = {
            "question": question,
            "options": options,
            "votes": [0]*len(options),
            "voters": {},
            "channel_id": target.id,
            "message_id": None,
            "created_by": interaction.user.id,
            "created_at": utc_now().isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "ended": False
        }
        save_config(cfg)
        
        view = self.build_poll_view(poll_id, question, options, [0]*len(options), interaction.user, end_time, False)
        content = ping_role.mention if ping_role else ""
        
        # Send poll to target channel FIRST
        msg = await target.send(content=content, view=view)
        
        # Save message ID
        cfg["polls"][poll_id]["message_id"] = msg.id
        save_config(cfg)
        
        # FIX: Respond with thinking=False - no thinking message
        success_view = make_simple_log_view("Poll Created", f"**{question}** in {target.mention}")
        await interaction.response.send_message(view=success_view, ephemeral=True)

    def build_poll_view(self, poll_id, question, options, votes, creator, end_time=None, ended=False):
        total = sum(votes) if sum(votes) > 0 else 1
        view = discord.ui.LayoutView(timeout=None)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"## {'📊 POLL' if not ended else '📊 POLL ENDED'}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"### {question}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        mention = creator.mention if hasattr(creator, 'mention') else f"<@{creator}>"
        if end_time:
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=datetime.timezone.utc)
            time_txt = f" • Ends <t:{int(end_time.timestamp())}:R>"
        else:
            time_txt = ""
        container.add_item(discord.ui.TextDisplay(f"{mention} • {sum(votes)} votes{time_txt}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        for idx, opt in enumerate(options):
            percent = (votes[idx] / total * 100) if sum(votes) > 0 else 0
            bar = make_bar(percent)
            container.add_item(discord.ui.TextDisplay(f"**{idx+1}. {opt}**\n`{bar}` **{percent:.1f}%** — {votes[idx]}"))
            if idx < len(options)-1:
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        row = discord.ui.ActionRow()
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
        for idx, opt in enumerate(options):
            row.add_item(discord.ui.Button(label=f"{opt[:30]}", style=discord.ButtonStyle.secondary, custom_id=f"poll_{poll_id}_{idx}", emoji=emojis[idx], disabled=ended))
        container.add_item(row)
        view.add_item(container)
        return view

    # ================= GIVEAWAY =================
    @app_commands.command(name="giveaway", description="Create giveaway")
    @app_commands.describe(
        prize="Prize", 
        winners="Winners", 
        duration="Minutes", 
        channel="Channel", 
        ping_role="Role to ping", 
        require_tag="Require tag?", 
        tag_text="Tag", 
        requirements="Requirements"
    )
    @app_commands.choices(require_tag=[app_commands.Choice(name="NO", value="no"), app_commands.Choice(name="YES", value="yes")])
    @app_commands.default_permissions(administrator=True)
    async def giveaway(self, interaction: discord.Interaction, prize: str, winners: int = 1, duration: int = 60, 
                       channel: typing.Optional[discord.TextChannel] = None, 
                       ping_role: typing.Optional[discord.Role] = None, 
                       require_tag: str = "no", 
                       tag_text: typing.Optional[str] = None, 
                       requirements: typing.Optional[str] = None):
        
        target = channel or interaction.channel
        end_time = utc_now() + datetime.timedelta(minutes=duration)
        cfg = load_config()
        if "giveaways" not in cfg: 
            cfg["giveaways"] = {}
        give_id = str(interaction.id)
        cfg["giveaways"][give_id] = {
            "prize": prize, 
            "winners": winners, 
            "end_time": end_time.isoformat(), 
            "channel_id": target.id, 
            "message_id": None, 
            "entries": [], 
            "require_tag": require_tag == "yes", 
            "tag_text": tag_text, 
            "requirements": requirements, 
            "hosted_by": interaction.user.id, 
            "ended": False
        }
        save_config(cfg)
        
        view = self.build_giveaway_view(give_id, prize, winners, end_time, interaction.user, 0, require_tag == "yes", tag_text, requirements)
        content = ping_role.mention if ping_role else ""
        msg = await target.send(content=content, view=view)
        
        cfg["giveaways"][give_id]["message_id"] = msg.id
        save_config(cfg)
        
        # FIX: No thinking
        success_view = make_simple_log_view("Giveaway Created", f"**{prize}** in {target.mention}")
        await interaction.response.send_message(view=success_view, ephemeral=True)

    def build_giveaway_view(self, give_id, prize, winners, end_time, creator, entries_count, require_tag, tag_text, requirements, ended=False, winners_list=None):
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=datetime.timezone.utc)
        view = discord.ui.LayoutView(timeout=None)

        if ended:
            container = discord.ui.Container()
            container.add_item(discord.ui.TextDisplay(f"## {LOGO} GIVEAWAY ENDED"))
            container.add_item(discord.ui.TextDisplay(f"### 🎁 {prize}"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(
                f"**Hosted by:** <@{creator.id if hasattr(creator,'id') else creator}>\n"
                f"**Ended:** <t:{int(end_time.timestamp())}:F>\n"
                f"**Total Entries:** `{entries_count}`"
            ))
            if winners_list:
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
                mentions = ", ".join([f"<@{uid}>" for uid in winners_list])
                container.add_item(discord.ui.TextDisplay(f"## 🏆 Winner{'s' if len(winners_list)>1 else ''}\n{mentions}\n\n-# Congratulations! Contact staff to claim your prize {LOGO}"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
            row = discord.ui.ActionRow()
            row.add_item(discord.ui.Button(label="Giveaway Ended", style=discord.ButtonStyle.secondary, custom_id=f"giveaway_ended_{give_id}", disabled=True))
            row.add_item(discord.ui.Button(label="Who Joined", style=discord.ButtonStyle.secondary, custom_id=f"giveaway_whojoined_{give_id}"))
            if winners_list:
                row.add_item(discord.ui.Button(label=f"{len(winners_list)} Winner{'s' if len(winners_list)>1 else ''}", style=discord.ButtonStyle.success, custom_id=f"giveaway_winners_{give_id}", disabled=True))
            container.add_item(row)
            view.add_item(container)
            return view

        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"## {LOGO} GIVEAWAY"))
        container.add_item(discord.ui.TextDisplay(f"### 🎁 {prize}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(discord.ui.TextDisplay(
            f"**🏆 Winners:** `{winners}`\n"
            f"**🎟 Entries:** `{entries_count}`\n"
            f"**⏰ Ends:** <t:{int(end_time.timestamp())}:R> — <t:{int(end_time.timestamp())}:F>\n"
            f"**👑 Host:** <@{creator.id if hasattr(creator,'id') else creator}>"
        ))
        if requirements or (require_tag and tag_text):
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            extra = ""
            if requirements:
                extra += f"**Requirements:** {requirements}\n"
            if require_tag and tag_text:
                extra += f"**Required Tag:** `{tag_text}`"
            container.add_item(discord.ui.TextDisplay(extra.strip()))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(discord.ui.TextDisplay(f"### How to enter?\nPress the button below — Good luck! {LOGO}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        row = discord.ui.ActionRow()
        row.add_item(discord.ui.Button(label="Enter Giveaway", style=discord.ButtonStyle.primary, custom_id=f"giveaway_enter_{give_id}"))
        row.add_item(discord.ui.Button(label=f"{entries_count} Entries", style=discord.ButtonStyle.secondary, custom_id=f"giveaway_info_{give_id}", disabled=True))
        row.add_item(discord.ui.Button(label="Who Joined", style=discord.ButtonStyle.secondary, custom_id=f"giveaway_whojoined_{give_id}"))
        container.add_item(row)
        row2 = discord.ui.ActionRow()
        row2.add_item(discord.ui.Button(label=f"Ends {end_time.strftime('%H:%M %d/%m')}", style=discord.ButtonStyle.secondary, custom_id=f"giveaway_time_{give_id}", disabled=True))
        container.add_item(row2)
        view.add_item(container)
        return view

    def build_who_joined_view(self, give_id, prize, entries):
        view = discord.ui.LayoutView(timeout=None)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"## {LOGO} WHO JOINED - {prize}"))
        container.add_item(discord.ui.TextDisplay(f"**Total:** `{len(entries)}` entries"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        if not entries:
            container.add_item(discord.ui.TextDisplay(f"**No one joined yet**\n-# Be the first!"))
        else:
            lines = []
            for idx, uid in enumerate(entries, 1):
                lines.append(f"`{idx}.` <@{uid}> - `{uid}`")
            text = "\n".join(lines)
            if len(text) > 3800:
                text = text[:3800] + f"\n-# +{len(entries)} total"
            container.add_item(discord.ui.TextDisplay(text))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"-# Prize: {prize} | <t:{int(utc_now().timestamp())}:R>"))
        view.add_item(container)
        return view

    # ================= BUTTON HANDLER - FIXED NO THINKING =================
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return
        cid = interaction.data["custom_id"]
        if not cid.startswith("poll_") and not cid.startswith("giveaway_"):
            return

        # FIX: Use thinking=False to avoid "Thinking..." message
        # For button clicks, we need to defer properly
        try:
            if cid.startswith("poll_") or "whojoined" in cid or "enter" in cid:
                # These need ephemeral response
                if not interaction.response.is_done():
                    # Important: ephemeral=True hides thinking for others, and we respond immediately after
                    await interaction.response.defer(ephemeral=True)
            else:
                # Info buttons - ignore or ephemeral
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=True)
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            print(f"Defer error: {e}")
            return

        if cid.startswith("poll_"):
            await self.handle_poll(interaction, cid)
        else:
            await self.handle_giveaway_button(interaction, cid)

    async def handle_poll(self, interaction: discord.Interaction, cid: str):
        try:
            _, poll_id, opt_idx = cid.split("_")
            opt_idx = int(opt_idx)
        except:
            try:
                await interaction.followup.send("Invalid poll", ephemeral=True)
            except:
                pass
            return
        
        cfg = load_config()
        poll = cfg.get("polls", {}).get(poll_id)
        if not poll or poll.get("ended"):
            try:
                await interaction.followup.send("Poll ended", ephemeral=True)
            except:
                pass
            return
        
        if poll.get("end_time"):
            et = parse_time(poll["end_time"])
            if utc_now() >= et:
                poll["ended"] = True
                cfg["polls"][poll_id] = poll
                save_config(cfg)
                try:
                    await interaction.followup.send("Poll has ended", ephemeral=True)
                except:
                    pass
                return
        
        user_id = str(interaction.user.id)
        old_vote = poll["voters"].get(user_id)
        if old_vote == opt_idx:
            try:
                await interaction.followup.send("You already voted for this option", ephemeral=True)
            except:
                pass
            return
        
        if old_vote is not None:
            poll["votes"][old_vote] -= 1
        poll["votes"][opt_idx] += 1
        poll["voters"][user_id] = opt_idx
        
        creator = interaction.guild.get_member(poll["created_by"]) if interaction.guild else None
        if not creator:
            creator = poll["created_by"]
        end_time = parse_time(poll["end_time"]) if poll.get("end_time") else None
        new_view = self.build_poll_view(poll_id, poll["question"], poll["options"], poll["votes"], creator, end_time, False)
        
        try:
            # Edit original message
            if interaction.message:
                await interaction.message.edit(view=new_view)
            else:
                ch = self.bot.get_channel(poll["channel_id"]) or await self.bot.fetch_channel(poll["channel_id"])
                msg = await ch.fetch_message(poll["message_id"])
                await msg.edit(view=new_view)
        except Exception as e:
            print(f"poll edit error: {e}")
        
        cfg["polls"][poll_id] = poll
        save_config(cfg)
        
        # FIX: No thinking, clean ephemeral confirm
        try:
            await interaction.followup.send(f"✅ Voted for **{poll['options'][opt_idx]}**", ephemeral=True)
        except:
            pass

    async def handle_giveaway_button(self, interaction: discord.Interaction, cid: str):
        if "whojoined" in cid:
            try:
                give_id = cid.split("_")[-1]
                cfg = load_config()
                give = cfg.get("giveaways", {}).get(give_id)
                if not give:
                    await interaction.followup.send("Giveaway not found", ephemeral=True)
                    return
                view = self.build_who_joined_view(give_id, give["prize"], give["entries"])
                await interaction.followup.send(view=view, ephemeral=True)
            except Exception as e:
                print(f"whojoined error {e}")
                try:
                    await interaction.followup.send(f"Error: {e}", ephemeral=True)
                except:
                    pass
            return
        
        if "info" in cid or "time" in cid or "winners" in cid or "ended" in cid:
            try:
                give_id = cid.split("_")[-1]
                cfg = load_config()
                give = cfg.get("giveaways", {}).get(give_id)
                if give:
                    et = parse_time(give["end_time"])
                    await interaction.followup.send(f"🎟 Entries: {len(give['entries'])}\n⏰ Ends: <t:{int(et.timestamp())}:F>\n🏆 Winners: {give['winners']}", ephemeral=True)
            except:
                pass
            return
        
        try:
            _, _, give_id = cid.split("_", 2)
        except:
            return
        
        cfg = load_config()
        give = cfg.get("giveaways", {}).get(give_id)
        if not give or give.get("ended"):
            try:
                await interaction.followup.send("Giveaway ended", ephemeral=True)
            except:
                pass
            return
        
        user_id = interaction.user.id
        if user_id in give["entries"]:
            try:
                await interaction.followup.send("✅ Already entered!", ephemeral=True)
            except:
                pass
            return
        
        give["entries"].append(user_id)
        end_time = parse_time(give["end_time"])
        creator = interaction.guild.get_member(give["hosted_by"]) if interaction.guild else give["hosted_by"]
        if not creator:
            creator = give["hosted_by"]
        
        new_view = self.build_giveaway_view(give_id, give["prize"], give["winners"], end_time, creator, len(give["entries"]), give.get("require_tag"), give.get("tag_text"), give.get("requirements"))
        
        try:
            if interaction.message:
                await interaction.message.edit(view=new_view)
            else:
                ch = self.bot.get_channel(give["channel_id"]) or await self.bot.fetch_channel(give["channel_id"])
                msg = await ch.fetch_message(give["message_id"])
                await msg.edit(view=new_view)
        except Exception as e:
            print(f"giveaway edit error: {e}")
        
        cfg["giveaways"][give_id] = give
        save_config(cfg)
        
        try:
            await interaction.followup.send(f"🎉 Entered **{give['prize']}**! Good luck {LOGO}", ephemeral=True)
        except:
            pass

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        await self.bot.wait_until_ready()
        cfg = load_config()
        giveaways = cfg.get("giveaways", {})
        now = utc_now()
        changed = False
        for give_id, give in list(giveaways.items()):
            if give.get("ended"): 
                continue
            try:
                end_time = parse_time(give["end_time"])
                if now >= end_time:
                    channel = self.bot.get_channel(give["channel_id"]) or await self.bot.fetch_channel(give["channel_id"])
                    if not channel: 
                        continue
                    try:
                        msg = await channel.fetch_message(give["message_id"])
                    except:
                        msg = None
                    entries = give["entries"]
                    winners_count = min(give["winners"], len(entries))
                    winners_list = random.sample(entries, winners_count) if entries else []
                    give["ended"] = True
                    give["winners_list"] = winners_list
                    changed = True
                    if msg:
                        creator = channel.guild.get_member(give["hosted_by"]) if channel.guild else give["hosted_by"]
                        end_view = self.build_giveaway_view(give_id, give["prize"], give["winners"], end_time, creator, len(entries), give.get("require_tag"), give.get("tag_text"), give.get("requirements"), ended=True, winners_list=winners_list)
                        await msg.edit(view=end_view)
                        if winners_list:
                            mentions = ", ".join([f"<@{uid}>" for uid in winners_list])
                            await channel.send(f"## 🎉 GIVEAWAY ENDED 🎉\n**Prize:** {give['prize']}\n**Winners:** {mentions}\n{LOGO}")
            except Exception as e:
                print(f"Giveaway check error: {e}")
                continue
        if changed:
            save_config(cfg)

    @tasks.loop(seconds=60)
    async def check_polls(self):
        await self.bot.wait_until_ready()
        cfg = load_config()
        polls = cfg.get("polls", {})
        now = utc_now()
        changed = False
        for poll_id, poll in list(polls.items()):
            if poll.get("ended"): 
                continue
            if not poll.get("end_time"): 
                continue
            try:
                end_time = parse_time(poll["end_time"])
                if now >= end_time:
                    channel = self.bot.get_channel(poll["channel_id"]) or await self.bot.fetch_channel(poll["channel_id"])
                    if not channel: 
                        continue
                    try:
                        msg = await channel.fetch_message(poll["message_id"])
                    except:
                        msg = None
                    poll["ended"] = True
                    changed = True
                    if msg:
                        creator = channel.guild.get_member(poll["created_by"]) if channel.guild else poll["created_by"]
                        end_view = self.build_poll_view(poll_id, poll["question"], poll["options"], poll["votes"], creator, end_time, ended=True)
                        await msg.edit(view=end_view)
            except Exception as e:
                print(f"Poll check error: {e}")
                continue
        if changed:
            save_config(cfg)

async def setup(bot):
    await bot.add_cog(PollsCog(bot))