import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.helpers import load_config, save_config
import asyncio, datetime

class InviteView(discord.ui.LayoutView):
    def __init__(self, cog, counts, guild, show_count=True):
        super().__init__(timeout=None)
        self.cog = cog
        self.counts = counts
        self.guild = guild
        self.show_count = show_count

        greeks = discord.PartialEmoji(name="GreeksLogo", id=1505682080330420244)
        c = discord.ui.Container() # No color
        c.add_item(discord.ui.TextDisplay(f"## {greeks} INVITE LEADERBOARD"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        if not counts:
            c.add_item(discord.ui.TextDisplay("> No invites yet - start inviting!\n> Use `/invite` to get your link"))
        else:
            for i, (uid, uses) in enumerate(counts[:10]):
                member = guild.get_member(int(uid))
                mention = member.mention if member else f"<@{uid}>"

                prefix = ["🥇", "🥈", "🥉"][i] if i < 3 else f"**{i+1}.**"

                if show_count:
                    c.add_item(discord.ui.TextDisplay(f"{prefix} {mention} — **{uses}** invites"))
                else:
                    c.add_item(discord.ui.TextDisplay(f"{prefix} {mention}"))

                if i < min(9, len(counts)-1):
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

            total = sum(u for _, u in counts)
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(discord.ui.TextDisplay(f"-# Total: {total} invites | {len(counts)} inviters | Updated <t:{int(discord.utils.utcnow().timestamp())}:R>"))

        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        row = discord.ui.ActionRow()
        row.add_item(discord.ui.Button(label="My Invites", style=discord.ButtonStyle.primary, custom_id="my_invites", emoji="👤"))
        row.add_item(discord.ui.Button(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh_board", emoji="🔄"))
        row.add_item(discord.ui.Button(label="Top 10", style=discord.ButtonStyle.secondary, custom_id="show_top", emoji="🏆"))
        c.add_item(row)
        self.add_item(c)

class InvitesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites_cache = {} # guild_id: {code: uses}
        self.inviter_cache = {} # guild_id: {code: inviter_id}
        self.leaderboard_loop.start()

    def cog_unload(self):
        self.leaderboard_loop.cancel()

    def _parse(self, invites):
        uses = {}
        inviters = {}
        for inv in invites:
            uses[inv.code] = inv.uses or 0
            if inv.inviter and not inv.inviter.bot:
                inviters[inv.code] = inv.inviter.id
        return uses, inviters

    async def ensure_cache(self, guild: discord.Guild):
        try:
            invites = await guild.invites()
            uses, inviters = self._parse(invites)
            self.invites_cache[guild.id] = uses
            self.inviter_cache[guild.id] = inviters
            return uses, inviters, invites
        except Exception as e:
            print(f"[Invites] cache fail {guild.id}: {e}")
            return {}, {}, []

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.ensure_cache(guild)
            await asyncio.sleep(0.5)
        print("[Invites] Cache loaded")

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        try:
            if not invite.guild: return
            gid = invite.guild.id
            if gid not in self.invites_cache:
                await self.ensure_cache(invite.guild)
                return
            self.invites_cache[gid][invite.code] = invite.uses or 0
            if invite.inviter and not invite.inviter.bot:
                self.inviter_cache[gid][invite.code] = invite.inviter.id
            await self.update_board_auto(gid)
        except Exception as e:
            print(f"invite_create {e}")

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        try:
            if not invite.guild: return
            gid = invite.guild.id
            if gid in self.invites_cache and invite.code in self.invites_cache[gid]:
                del self.invites_cache[gid][invite.code]
            if gid in self.inviter_cache and invite.code in self.inviter_cache[gid]:
                del self.inviter_cache[gid][invite.code]
            await self.update_board_auto(gid)
        except: pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot: return
        guild = member.guild
        try:
            # Get old cache
            old_uses = self.invites_cache.get(guild.id)
            old_inviters = self.inviter_cache.get(guild.id, {})

            if old_uses is None:
                await self.ensure_cache(guild)
                return

            # Wait a bit so Discord updates invite uses
            await asyncio.sleep(1.5)
            new_invites = await guild.invites()
            new_uses, new_inviters = self._parse(new_invites)

            # FIND WHICH INVITE WAS USED
            used_code = None
            inviter_id = None

            for code, new_count in new_uses.items():
                old_count = old_uses.get(code, 0)
                if new_count > old_count:
                    used_code = code
                    inviter_id = new_inviters.get(code) or old_inviters.get(code)
                    break

            # Check vanity or widget if no invite found
            if not inviter_id:
                # Could be vanity URL or direct join
                # Try to find in audit or just ignore
                print(f"[Invites] {member} joined but no invite found (vanity/direct)")

            # Update cache BEFORE saving
            self.invites_cache[guild.id] = new_uses
            self.inviter_cache[guild.id] = {**old_inviters, **new_inviters}

            if inviter_id and inviter_id!= member.id: # Don't count self-invite
                cfg = load_config()
                if "invite_counts" not in cfg: cfg["invite_counts"] = {}
                if "invite_history" not in cfg: cfg["invite_history"] = {}

                # Anti-fake: check if user already in history (rejoin)
                prev = cfg["invite_history"].get(str(member.id))
                if prev:
                    # User left and rejoined - don't count again if same inviter
                    old_inviter = prev.get("invited_by")
                    if old_inviter == inviter_id:
                        print(f"[Invites] {member} rejoined, same inviter, not counting")
                    else:
                        # Different inviter, remove from old and add to new
                        old_uid = str(old_inviter)
                        if old_uid in cfg["invite_counts"]:
                            cfg["invite_counts"][old_uid] = max(0, cfg["invite_counts"][old_uid] - 1)

                uid_str = str(inviter_id)
                cfg["invite_counts"][uid_str] = cfg["invite_counts"].get(uid_str, 0) + 1

                cfg["invite_history"][str(member.id)] = {
                    "invited_by": inviter_id,
                    "code": used_code,
                    "at": int(discord.utils.utcnow().timestamp()),
                    "name": str(member)
                }
                save_config(cfg)
                print(f"[Invites] {member} invited by {inviter_id} using {used_code}")

                # Log in logs channel
                log_ch_id = cfg.get("channels", {}).get("logs")
                if log_ch_id:
                    log_ch = guild.get_channel(log_ch_id)
                    if log_ch:
                        try:
                            inviter = guild.get_member(inviter_id)
                            inviter_mention = inviter.mention if inviter else f"<@{inviter_id}>"
                            view = discord.ui.LayoutView()
                            cc = discord.ui.Container()
                            cc.add_item(discord.ui.TextDisplay(f"### 📨 Member Joined via Invite\n**New Member:** {member.mention} ({member.id})\n**Invited by:** {inviter_mention}\n**Code:** `{used_code}`\n**Total Invites:** {cfg['invite_counts'][uid_str]}"))
                            view.add_item(cc)
                            await log_ch.send(view=view)
                        except: pass

            await self.update_board_auto(guild.id)

        except Exception as e:
            print(f"[Invites] join error {e}")
            await self.ensure_cache(guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # When member leaves, subtract from inviter
        try:
            cfg = load_config()
            history = cfg.get("invite_history", {})
            data = history.get(str(member.id))
            if data:
                inviter_id = str(data.get("invited_by"))
                if inviter_id and inviter_id in cfg.get("invite_counts", {}):
                    cfg["invite_counts"][inviter_id] = max(0, cfg["invite_counts"][inviter_id] - 1)
                    save_config(cfg)
                    await self.update_board_auto(member.guild.id)
        except: pass

    @tasks.loop(seconds=60)
    async def leaderboard_loop(self):
        await self.bot.wait_until_ready()
        cfg = load_config()
        ch_id = cfg.get("channels", {}).get("invite_leaderboard")
        if not ch_id: return
        for g in self.bot.guilds:
            ch = g.get_channel(ch_id)
            if ch:
                try:
                    await self.update_board(ch)
                except: pass

    @leaderboard_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    async def get_sorted_counts(self, guild):
        cfg = load_config()
        counts = cfg.get("invite_counts", {}).copy()
        # Filter out 0
        sorted_counts = sorted([(uid, uses) for uid, uses in counts.items() if uses > 0], key=lambda x: x[1], reverse=True)
        return sorted_counts

    async def update_board_auto(self, guild_id):
        cfg = load_config()
        ch_id = cfg.get("channels", {}).get("invite_leaderboard")
        if not ch_id: return
        guild = self.bot.get_guild(guild_id)
        if not guild: return
        ch = guild.get_channel(ch_id)
        if ch:
            await self.update_board(ch)

    async def update_board(self, channel):
        cfg = load_config()
        show_count = cfg.get("settings", {}).get("invite_show_count", True)
        sorted_counts = await self.get_sorted_counts(channel.guild)
        view = InviteView(self, sorted_counts, channel.guild, show_count=show_count)
        try:
            # Find existing bot message
            found = None
            async for msg in channel.history(limit=50):
                if msg.author.id == self.bot.user.id and msg.components:
                    # Check if it's our leaderboard (has buttons)
                    found = msg
                    break
            if found:
                try:
                    await found.edit(view=view)
                    return
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(f"edit fail {e}")
            # If no message or edit failed, send new
            # First purge old bot messages to avoid duplicates
            async for msg in channel.history(limit=20):
                if msg.author.id == self.bot.user.id:
                    try: await msg.delete()
                    except: pass
            await channel.send(view=view)
        except Exception as e:
            print(f"board error {e}")

    @app_commands.command(name="setup_invites", description="Set invite leaderboard channel")
    @app_commands.describe(channel="Channel for leaderboard", show_invite_count="Show invite count?")
    @app_commands.default_permissions(administrator=True)
    async def setup_invites(self, interaction: discord.Interaction, channel: discord.TextChannel, show_invite_count: bool = True):
        cfg = load_config()
        if "channels" not in cfg: cfg["channels"] = {}
        if "settings" not in cfg: cfg["settings"] = {}
        cfg["channels"]["invite_leaderboard"] = channel.id
        cfg["settings"]["invite_show_count"] = show_invite_count
        save_config(cfg)
        await self.ensure_cache(interaction.guild)
        await interaction.response.defer(ephemeral=True)
        await self.update_board(channel)
        await interaction.followup.send(f"✅ Leaderboard set to {channel.mention} | Auto-update every 60s + on join", ephemeral=True)

    @app_commands.command(name="inviteboard", description="Force update leaderboard")
    @app_commands.default_permissions(administrator=True)
    async def inviteboard(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        ch_id = cfg.get("channels", {}).get("invite_leaderboard")
        await self.ensure_cache(interaction.guild)
        target = channel or (interaction.guild.get_channel(ch_id) if ch_id else interaction.channel)
        await self.update_board(target)
        await interaction.followup.send(f"✅ Updated {target.mention}", ephemeral=True)

    @app_commands.command(name="invites", description="Check your invites")
    async def invites_cmd(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        target = user or interaction.user
        sorted_counts = await self.get_sorted_counts(interaction.guild)
        my = 0
        rank = 0
        for i, (uid, uses) in enumerate(sorted_counts):
            if uid == str(target.id):
                my = uses
                rank = i+1
                break
        cfg = load_config()
        show_count = cfg.get("settings", {}).get("invite_show_count", True)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        if show_count:
            text = f"## 👤 YOUR INVITES\n{target.mention} has **{my}** invites" + (f"\nRank: **#{rank}**" if rank else "\nNot ranked yet")
        else:
            text = f"## 👤 YOUR INVITES\nRank **#{rank}**" if rank else "Not ranked"
        c.add_item(discord.ui.TextDisplay(text))
        view.add_item(c)
        await interaction.followup.send(view=view, ephemeral=True)

    @app_commands.command(name="reset_invites", description="Reset leaderboard")
    @app_commands.default_permissions(administrator=True)
    async def reset_invites(self, interaction: discord.Interaction):
        cfg = load_config()
        cfg["invite_counts"] = {}
        if "invite_history" in cfg: cfg["invite_history"] = {}
        save_config(cfg)
        self.invites_cache = {}
        self.inviter_cache = {}
        await self.ensure_cache(interaction.guild)
        await interaction.response.send_message("✅ Reset done", ephemeral=True)
        await self.update_board_auto(interaction.guild.id)

    @app_commands.command(name="sync_invites", description="Sync from real Discord invites - FIXES stuck leaderboard")
    @app_commands.default_permissions(administrator=True)
    async def sync_invites(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            invites = await interaction.guild.invites()
            temp = {}
            for inv in invites:
                if inv.inviter and not inv.inviter.bot:
                    uid = str(inv.inviter.id)
                    temp[uid] = temp.get(uid, 0) + (inv.uses or 0)
            cfg = load_config()
            cfg["invite_counts"] = temp
            save_config(cfg)
            await self.ensure_cache(interaction.guild)
            await self.update_board_auto(interaction.guild.id)
            await interaction.followup.send(f"✅ Synced {len(temp)} inviters, {sum(temp.values())} total invites - FIXED!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="remove_invites", description="Remove invites from user")
    @app_commands.default_permissions(administrator=True)
    async def remove_invites(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        cfg = load_config()
        if "invite_counts" not in cfg: cfg["invite_counts"] = {}
        uid = str(user.id)
        cfg["invite_counts"][uid] = max(0, cfg["invite_counts"].get(uid, 0) - amount)
        save_config(cfg)
        await interaction.response.send_message(f"✅ Removed {amount} from {user.mention} - Now {cfg['invite_counts'][uid]}", ephemeral=True)
        await self.update_board_auto(interaction.guild.id)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        cid = interaction.data["custom_id"]
        if cid not in ["my_invites", "refresh_board", "show_top"]: return
        cfg = load_config()
        show_count = cfg.get("settings", {}).get("invite_show_count", True)

        if cid == "my_invites":
            await interaction.response.defer(ephemeral=True)
            sorted_counts = await self.get_sorted_counts(interaction.guild)
            my = 0
            rank = 0
            for i, (uid, uses) in enumerate(sorted_counts):
                if uid == str(interaction.user.id):
                    my = uses
                    rank = i+1
                    break
            view = discord.ui.LayoutView()
            c = discord.ui.Container()
            txt = f"## 👤 MY INVITES\n{interaction.user.mention} - **{my}** invites\nRank: **#{rank}**" if rank else "## MY INVITES\n0 invites - start inviting!"
            c.add_item(discord.ui.TextDisplay(txt))
            view.add_item(c)
            await interaction.followup.send(view=view, ephemeral=True)

        elif cid == "refresh_board":
            await interaction.response.defer(ephemeral=True)
            await self.ensure_cache(interaction.guild)
            await self.update_board_auto(interaction.guild.id)
            await interaction.followup.send("✅ Refreshed and synced!", ephemeral=True)

        elif cid == "show_top":
            await interaction.response.defer(ephemeral=True)
            sorted_counts = await self.get_sorted_counts(interaction.guild)
            txt = "## 🏆 TOP 10\n"
            for i, (uid, uses) in enumerate(sorted_counts[:10]):
                m = interaction.guild.get_member(int(uid))
                mention = m.mention if m else f"<@{uid}>"
                medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}."
                txt += f"{medal} {mention} - {uses}\n" if show_count else f"{medal} {mention}\n"
            if not sorted_counts:
                txt = "No invites yet"
            view = discord.ui.LayoutView()
            c = discord.ui.Container()
            c.add_item(discord.ui.TextDisplay(txt))
            view.add_item(c)
            await interaction.followup.send(view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(InvitesCog(bot))