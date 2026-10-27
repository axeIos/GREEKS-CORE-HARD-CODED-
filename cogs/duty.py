import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import load_config, save_config
import datetime, time

class DutyView(discord.ui.LayoutView):
    def __init__(self, times, guild, required_role, voice_times=None):
        super().__init__(timeout=None)
        times_with_live = dict(times)
        if voice_times:
            now = time.time()
            for uid, join_t in voice_times.items():
                times_with_live[str(uid)] = times_with_live.get(str(uid), 0) + int(now - join_t)
        sorted_times = sorted(times_with_live.items(), key=lambda x: x[1], reverse=True)[:10]
        c = discord.ui.Container()
        title = f"## ⏰ DUTY LEADERBOARD"
        if required_role:
            title += f" - {required_role.name}"
        c.add_item(discord.ui.TextDisplay(title))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        if required_role:
            c.add_item(discord.ui.TextDisplay(f"Only counts time in VC for members with {required_role.mention}"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        if not sorted_times:
            c.add_item(discord.ui.TextDisplay("No duty time yet"))
        else:
            for i, (uid, secs) in enumerate(sorted_times):
                member = guild.get_member(int(uid))
                mention = member.mention if member else f"<@{uid}>"
                h = secs // 3600
                m = (secs % 3600) // 60
                medal = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"**{i+1}.**"
                c.add_item(discord.ui.TextDisplay(f"{medal} {mention} — **{h}h {m}m**"))
                if i < len(sorted_times)-1:
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        total = sum(times_with_live.values())
        total_h = total // 3600
        total_m = (total % 3600) // 60
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        c.add_item(discord.ui.TextDisplay(f"Total: **{total_h}h {total_m}m** | Updated: <t:{int(time.time())}:R>"))
        row = discord.ui.ActionRow()
        row.add_item(discord.ui.Button(label="My Time", style=discord.ButtonStyle.primary, custom_id="my_duty_time"))
        row.add_item(discord.ui.Button(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh_duty"))
        c.add_item(row)
        self.add_item(c)

class DutyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_times = {}
        self.duty_loop.start()

    def _get_tracked_vcs(self, duty):
        vcs = duty.get("voice_channels")
        if vcs is not None:
            return vcs
        old = duty.get("voice_channel")
        return [old] if old else []

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        cfg = load_config()
        duty = cfg["settings"].get("duty", {})
        required_id = duty.get("required_role")
        on_role_id = duty.get("on_role")
        off_role_id = duty.get("off_role")
        tracked_vcs = self._get_tracked_vcs(duty)
        guild = member.guild
        required_role = guild.get_role(required_id) if required_id else None
        on_role = guild.get_role(on_role_id) if on_role_id else None
        off_role = guild.get_role(off_role_id) if off_role_id else None
        if required_role and required_role not in member.roles:
            return
        def is_tracked(channel):
            if not channel:
                return False
            if not tracked_vcs:
                return True
            return channel.id in tracked_vcs
        if before.channel is None and after.channel is not None:
            if not is_tracked(after.channel):
                return
            self.voice_times[member.id] = time.time()
            try:
                if on_role and on_role not in member.roles:
                    await member.add_roles(on_role, reason="Joined VC")
                if off_role and off_role in member.roles:
                    await member.remove_roles(off_role, reason="Joined VC")
            except:
                pass
        elif before.channel is not None and after.channel is None:
            if not is_tracked(before.channel):
                return
            join_time = self.voice_times.pop(member.id, None)
            if join_time:
                duration = int(time.time() - join_time)
                if "duty_times" not in cfg:
                    cfg["duty_times"] = {}
                uid = str(member.id)
                cfg["duty_times"][uid] = cfg["duty_times"].get(uid, 0) + duration
                save_config(cfg)
            try:
                if on_role and on_role in member.roles:
                    await member.remove_roles(on_role, reason="Left VC")
                if off_role and off_role not in member.roles:
                    await member.add_roles(off_role, reason="Left VC")
            except:
                pass
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            before_tracked = is_tracked(before.channel)
            after_tracked = is_tracked(after.channel)
            if before_tracked and not after_tracked:
                join_time = self.voice_times.pop(member.id, None)
                if join_time:
                    duration = int(time.time() - join_time)
                    if "duty_times" not in cfg:
                        cfg["duty_times"] = {}
                    uid = str(member.id)
                    cfg["duty_times"][uid] = cfg["duty_times"].get(uid, 0) + duration
                    save_config(cfg)

    @tasks.loop(minutes=5)
    async def duty_loop(self):
        cfg = load_config()
        ch_id = cfg["channels"].get("duty_leaderboard")
        if not ch_id:
            return
        for guild in self.bot.guilds:
            ch = guild.get_channel(ch_id)
            if ch:
                await self.update_duty_board(ch)

    @duty_loop.before_loop
    async def before_duty_loop(self):
        await self.bot.wait_until_ready()

    async def update_duty_board(self, channel):
        cfg = load_config()
        times = cfg.get("duty_times", {})
        duty = cfg["settings"].get("duty", {})
        required_id = duty.get("required_role")
        required_role = channel.guild.get_role(required_id) if required_id else None
        view = DutyView(times, channel.guild, required_role, voice_times=self.voice_times)
        try:
            async for msg in channel.history(limit=20):
                if msg.author == self.bot.user:
                    await msg.edit(view=view)
                    return
            await channel.send(view=view)
        except:
            try:
                await channel.send(view=view)
            except:
                pass

    @app_commands.command(name="setup_duty", description="Setup duty leaderboard")
    @app_commands.default_permissions(administrator=True)
    async def setup_duty(self, interaction: discord.Interaction, required_role: discord.Role, leaderboard_channel: discord.TextChannel = None, voice_channel: discord.VoiceChannel = None, voice_channel2: discord.VoiceChannel = None, voice_channel3: discord.VoiceChannel = None, voice_channel4: discord.VoiceChannel = None):
        cfg = load_config()
        if "duty" not in cfg["settings"]:
            cfg["settings"]["duty"] = {}
        cfg["settings"]["duty"]["required_role"] = required_role.id
        vcs = []
        for vc in [voice_channel, voice_channel2, voice_channel3, voice_channel4]:
            if vc:
                vcs.append(vc.id)
        cfg["settings"]["duty"]["voice_channels"] = vcs
        if leaderboard_channel:
            cfg["channels"]["duty_leaderboard"] = leaderboard_channel.id
        save_config(cfg)
        await interaction.response.defer(ephemeral=True)
        if leaderboard_channel:
            await self.update_duty_board(leaderboard_channel)
        await interaction.followup.send("Setup done", ephemeral=True)

    @app_commands.command(name="dutyboard", description="Update duty leaderboard now")
    @app_commands.default_permissions(administrator=True)
    async def dutyboard(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        ch_id = cfg["channels"].get("duty_leaderboard")
        target = channel or (interaction.guild.get_channel(ch_id) if ch_id else None) or interaction.channel
        await self.update_duty_board(target)
        await interaction.followup.send(f"Updated {target.mention}", ephemeral=True)

    @app_commands.command(name="dutystats", description="Check duty time")
    async def dutystats(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        cfg = load_config()
        secs = cfg.get("duty_times", {}).get(str(target.id), 0)
        if target.id in self.voice_times:
            secs += int(time.time() - self.voice_times[target.id])
        h = secs // 3600
        m = (secs % 3600) // 60
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"{target.mention} has **{h}h {m}m**"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.command(name="my_time", description="Check your duty time")
    async def my_time(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        secs = load_config().get("duty_times", {}).get(str(interaction.user.id), 0)
        if interaction.user.id in self.voice_times:
            secs += int(time.time() - self.voice_times[interaction.user.id])
        h = secs // 3600
        m = (secs % 3600) // 60
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"You have **{h}h {m}m**"))
        view.add_item(c)
        await interaction.followup.send(view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return
        cid = interaction.data["custom_id"]
        if cid == "my_duty_time":
            await interaction.response.defer(ephemeral=True)
            cfg = load_config()
            secs = cfg.get("duty_times", {}).get(str(interaction.user.id), 0)
            if interaction.user.id in self.voice_times:
                secs += int(time.time() - self.voice_times[interaction.user.id])
            h = secs // 3600
            m = (secs % 3600) // 60
            view = discord.ui.LayoutView()
            c = discord.ui.Container()
            c.add_item(discord.ui.TextDisplay(f"You have **{h}h {m}m**"))
            view.add_item(c)
            await interaction.followup.send(view=view, ephemeral=True)
        elif cid == "refresh_duty":
            await interaction.response.defer()
            cfg = load_config()
            times = cfg.get("duty_times", {})
            duty = cfg["settings"].get("duty", {})
            required_id = duty.get("required_role")
            required_role = interaction.guild.get_role(required_id) if required_id else None
            view = DutyView(times, interaction.guild, required_role, voice_times=self.voice_times)
            try:
                await interaction.edit_original_response(view=view)
            except:
                try:
                    await interaction.message.edit(view=view)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(DutyCog(bot))