import discord
from discord.ext import commands
from discord import app_commands
from helpers import load_config, save_config
import datetime

NO_PING = discord.AllowedMentions.none()

def now_ts():
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp())

class LogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="logs_setup", description="Setup ALL logs - ULTIMATE NO PING")
    @app_commands.describe(
        message="Message logs (delete/edit/bulk)",
        member="Member join/leave",
        moderation="Bans/kicks/mutes/timeouts",
        voice="Voice logs",
        role="Role logs",
        channel="Channel logs",
        invite="Invite logs",
        server="Server/emoji/sticker/webhook logs",
        thread="Thread logs"
    )
    @app_commands.default_permissions(administrator=True)
    async def logs_setup(self, interaction: discord.Interaction,
        message: discord.TextChannel = None,
        member: discord.TextChannel = None,
        moderation: discord.TextChannel = None,
        voice: discord.TextChannel = None,
        role: discord.TextChannel = None,
        channel: discord.TextChannel = None,
        invite: discord.TextChannel = None,
        server: discord.TextChannel = None,
        thread: discord.TextChannel = None
    ):
        cfg = load_config()
        cfg["channels"]["logs_message_delete"] = message.id if message else cfg["channels"].get("logs_message_delete")
        cfg["channels"]["logs_message_edit"] = message.id if message else cfg["channels"].get("logs_message_edit")
        cfg["channels"]["logs_member_join"] = member.id if member else cfg["channels"].get("logs_member_join")
        cfg["channels"]["logs_member_leave"] = member.id if member else cfg["channels"].get("logs_member_leave")
        cfg["channels"]["logs_moderation"] = moderation.id if moderation else cfg["channels"].get("logs_moderation")
        cfg["channels"]["logs_voice"] = voice.id if voice else cfg["channels"].get("logs_voice")
        cfg["channels"]["logs_role"] = role.id if role else cfg["channels"].get("logs_role")
        cfg["channels"]["logs_channel"] = channel.id if channel else cfg["channels"].get("logs_channel")
        cfg["channels"]["logs_invite"] = invite.id if invite else cfg["channels"].get("logs_invite")
        cfg["channels"]["logs_server"] = server.id if server else cfg["channels"].get("logs_server")
        cfg["channels"]["logs_thread"] = thread.id if thread else cfg["channels"].get("logs_thread")
        save_config(cfg)

        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## LOGS SETUP - ULTIMATE NO PING"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Message:** `{message.name if message else 'Not changed'}`\n**Member:** `{member.name if member else 'Not changed'}`\n**Mod:** `{moderation.name if moderation else 'Not changed'}`\n**Voice:** `{voice.name if voice else 'Not changed'}`\n**Role:** `{role.name if role else 'Not changed'}`\n**Channel:** `{channel.name if channel else 'Not changed'}`\n**Invite:** `{invite.name if invite else 'Not changed'}`\n**Server:** `{server.name if server else 'Not changed'}`\n**Thread:** `{thread.name if thread else 'Not changed'}`"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"-# All logs with full info: who did what to whom + time + reason + audit log | NO PING"))
        view.add_item(c)
        await interaction.response.send_message(view=view, ephemeral=True, allowed_mentions=NO_PING)

    def get_ch(self, guild, key):
        cfg = load_config()
        ch_id = cfg["channels"].get(key)
        if not ch_id:
            ch_id = cfg["channels"].get("logs")
        if not ch_id:
            return None
        return guild.get_channel(ch_id)

    async def get_audit(self, guild, action, target_id=None):
        try:
            async for entry in guild.audit_logs(limit=3, action=action):
                if target_id and entry.target and entry.target.id != target_id:
                    continue
                mod = f"`{entry.user.display_name}` | ID `{entry.user.id}`"
                reason = entry.reason or "No reason"
                return mod, reason
        except:
            pass
        return "Unknown / No perms", "No reason"

    # ========== MESSAGE ==========
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot:
            return
        ch = self.get_ch(message.guild, "logs_message_delete")
        if not ch: return
        mod, reason = await self.get_audit(message.guild, discord.AuditLogAction.message_delete, message.author.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## MESSAGE DELETED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Author:** `{message.author.display_name}` (`{message.author}`) | ID `{message.author.id}`\n**Channel:** `{message.channel.name}` | ID `{message.channel.id}`\n**Message ID:** `{message.id}`\n**Created:** <t:{int(message.created_at.timestamp())}:F> | <t:{int(message.created_at.timestamp())}:R>\n**Deleted At:** <t:{now_ts()}:F>"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Content:**\n{message.content[:1500] or '*No text / embed / image*'}"))
        if message.attachments:
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(discord.ui.TextDisplay(f"**Attachments ({len(message.attachments)}):**\n" + "\n".join([a.url for a in message.attachments][:5])[:1000]))
        if message.stickers:
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(discord.ui.TextDisplay(f"**Stickers:** {', '.join([s.name for s in message.stickers])}"))
        if message.reference:
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(discord.ui.TextDisplay(f"**Reply To:** Message ID `{message.reference.message_id}`"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Audit - Deleted By:** {mod}\n**Reason:** `{reason}`"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages or not messages[0].guild:
            return
        ch = self.get_ch(messages[0].guild, "logs_message_delete")
        if not ch: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## BULK DELETE - {len(messages)} messages"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Guild:** `{messages[0].guild.name}` | ID `{messages[0].guild.id}`\n**Channels:** {', '.join(set([f'`{m.channel.name}`' for m in messages]))[:500]}\n**Authors:** {', '.join(set([f'`{m.author.display_name}` ({m.author.id})' for m in messages if not m.author.bot]))[:800]}\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        ch = self.get_ch(before.guild, "logs_message_delete")
        if not ch: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## MESSAGE EDITED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Author:** `{before.author.display_name}` | ID `{before.author.id}`\n**Channel:** `{before.channel.name}` | ID `{before.channel.id}`\n**Message ID:** `{before.id}` | [Jump](https://discord.com/channels/{before.guild.id}/{before.channel.id}/{before.id})\n**Edited At:** <t:{now_ts()}:F>"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Before:**\n{before.content[:1000] or '*No text*'}"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**After:**\n{after.content[:1000] or '*No text*'}"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    # ========== MEMBER ==========
    @commands.Cog.listener()
    async def on_member_join(self, member):
        ch = self.get_ch(member.guild, "logs_member_join")
        if not ch: return
        age = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## MEMBER JOINED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**User:** `{member.display_name}` | `{member}` | ID `{member.id}`\n**Account Created:** <t:{int(member.created_at.timestamp())}:F> (<t:{int(member.created_at.timestamp())}:R>) | **{age} days old**\n**Joined At:** <t:{now_ts()}:F>\n**Members:** `{member.guild.member_count}`\n**Bot:** `{member.bot}`"))
        if age < 7:
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(discord.ui.TextDisplay(f"⚠ **NEW ACCOUNT - {age} days old!**"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        ch = self.get_ch(member.guild, "logs_member_leave")
        if not ch: return
        roles = ", ".join([f"`{r.name}`" for r in getattr(member, 'roles', []) if r.name != "@everyone"])[:1000] or "None"
        mod, reason = await self.get_audit(member.guild, discord.AuditLogAction.kick, member.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## MEMBER LEFT / KICKED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**User:** `{member.display_name}` | `{member}` | ID `{member.id}`\n**Joined At:** <t:{int(member.joined_at.timestamp())}:F> if {member.joined_at} else 'Unknown'\n**Roles Had:** {roles}\n**Left At:** <t:{now_ts()}:F>\n**Members Now:** `{member.guild.member_count}`"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Possible Kicker:** {mod}\n**Reason:** `{reason}`"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        ch = self.get_ch(guild, "logs_moderation")
        if not ch: return
        mod, reason = await self.get_audit(guild, discord.AuditLogAction.ban, user.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## MEMBER BANNED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**User:** `{user.display_name}` | `{user}` | ID `{user.id}`\n**Account Created:** <t:{int(user.created_at.timestamp())}:F> (<t:{int(user.created_at.timestamp())}:R>)\n**Banned At:** <t:{now_ts()}:F>\n**Banned By:** {mod}\n**Reason:** `{reason}`"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        ch = self.get_ch(guild, "logs_moderation")
        if not ch: return
        mod, reason = await self.get_audit(guild, discord.AuditLogAction.unban, user.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## MEMBER UNBANNED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**User:** `{user}` | ID `{user.id}`\n**Unbanned By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Nickname
        if before.nick != after.nick:
            ch = self.get_ch(after.guild, "logs_server") or self.get_ch(after.guild, "logs_moderation")
            if ch:
                mod, reason = await self.get_audit(after.guild, discord.AuditLogAction.member_update, after.id)
                view = discord.ui.LayoutView()
                c = discord.ui.Container()
                c.add_item(discord.ui.TextDisplay(f"## NICKNAME CHANGED"))
                c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                c.add_item(discord.ui.TextDisplay(f"**User:** `{after.display_name}` | `{after}` | ID `{after.id}`\n**Before:** `{before.nick or before.name}`\n**After:** `{after.nick or after.name}`\n**Changed By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
                view.add_item(c)
                await ch.send(view=view, allowed_mentions=NO_PING)
        # Roles
        if before.roles != after.roles:
            ch = self.get_ch(after.guild, "logs_role")
            if ch:
                added = [r for r in after.roles if r not in before.roles]
                removed = [r for r in before.roles if r not in after.roles]
                mod, reason = await self.get_audit(after.guild, discord.AuditLogAction.member_role_update, after.id)
                if added:
                    view = discord.ui.LayoutView()
                    c = discord.ui.Container()
                    c.add_item(discord.ui.TextDisplay(f"## ROLE ADDED"))
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    c.add_item(discord.ui.TextDisplay(f"**User:** `{after.display_name}` | `{after}` | ID `{after.id}`\n**Added:** {', '.join([f'`{r.name}` (ID `{r.id}`)' for r in added])}\n**All Now:** {', '.join([f'`{r.name}`' for r in after.roles if r.name != '@everyone']) or 'None'}\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
                    view.add_item(c)
                    await ch.send(view=view, allowed_mentions=NO_PING)
                if removed:
                    view = discord.ui.LayoutView()
                    c = discord.ui.Container()
                    c.add_item(discord.ui.TextDisplay(f"## ROLE REMOVED"))
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    c.add_item(discord.ui.TextDisplay(f"**User:** `{after.display_name}` | `{after}` | ID `{after.id}`\n**Removed:** {', '.join([f'`{r.name}` (ID `{r.id}`)' for r in removed])}\n**All Now:** {', '.join([f'`{r.name}`' for r in after.roles if r.name != '@everyone']) or 'None'}\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
                    view.add_item(c)
                    await ch.send(view=view, allowed_mentions=NO_PING)
        # Timeout
        if before.is_timed_out() != after.is_timed_out() or before.timed_out_until != after.timed_out_until:
            ch = self.get_ch(after.guild, "logs_moderation")
            if ch:
                mod, reason = await self.get_audit(after.guild, discord.AuditLogAction.member_update, after.id)
                view = discord.ui.LayoutView()
                c = discord.ui.Container()
                if after.is_timed_out():
                    c.add_item(discord.ui.TextDisplay(f"## TIMEOUT ADDED"))
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    c.add_item(discord.ui.TextDisplay(f"**User:** `{after.display_name}` | ID `{after.id}`\n**Until:** <t:{int(after.timed_out_until.timestamp())}:F> if after.timed_out_until else 'Unknown'\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
                else:
                    c.add_item(discord.ui.TextDisplay(f"## TIMEOUT REMOVED"))
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    c.add_item(discord.ui.TextDisplay(f"**User:** `{after.display_name}` | ID `{after.id}`\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
                view.add_item(c)
                await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        for guild in self.bot.guilds:
            mem = guild.get_member(after.id)
            if not mem: continue
            if before.name != after.name:
                ch = self.get_ch(guild, "logs_server")
                if ch:
                    view = discord.ui.LayoutView()
                    c = discord.ui.Container()
                    c.add_item(discord.ui.TextDisplay(f"## USERNAME CHANGED"))
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    c.add_item(discord.ui.TextDisplay(f"**User:** `{after.display_name}` | ID `{after.id}`\n**Before:** `{before.name}`\n**After:** `{after.name}`\n**Time:** <t:{now_ts()}:F>"))
                    view.add_item(c)
                    await ch.send(view=view, allowed_mentions=NO_PING)
            if before.display_avatar != after.display_avatar:
                ch = self.get_ch(guild, "logs_server")
                if ch:
                    view = discord.ui.LayoutView()
                    c = discord.ui.Container()
                    c.add_item(discord.ui.TextDisplay(f"## AVATAR CHANGED"))
                    c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    c.add_item(discord.ui.TextDisplay(f"**User:** `{after.display_name}` | `{after}` | ID `{after.id}`\n**Time:** <t:{now_ts()}:F>"))
                    view.add_item(c)
                    await ch.send(view=view, allowed_mentions=NO_PING)

    # ========== VOICE ==========
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        ch = self.get_ch(member.guild, "logs_voice")
        if not ch: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        if before.channel != after.channel:
            if not before.channel and after.channel:
                c.add_item(discord.ui.TextDisplay(f"## VOICE JOINED"))
                c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                c.add_item(discord.ui.TextDisplay(f"**User:** `{member.display_name}` | `{member}` | ID `{member.id}`\n**Channel:** `{after.channel.name}` | ID `{after.channel.id}`\n**Members in VC:** `{len(after.channel.members)}`\n**Time:** <t:{now_ts()}:F>"))
            elif before.channel and not after.channel:
                c.add_item(discord.ui.TextDisplay(f"## VOICE LEFT"))
                c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                c.add_item(discord.ui.TextDisplay(f"**User:** `{member.display_name}` | ID `{member.id}`\n**Channel:** `{before.channel.name}` | ID `{before.channel.id}`\n**Time:** <t:{now_ts()}:F>"))
            else:
                c.add_item(discord.ui.TextDisplay(f"## VOICE MOVED"))
                c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                c.add_item(discord.ui.TextDisplay(f"**User:** `{member.display_name}` | ID `{member.id}`\n**From:** `{before.channel.name}` (ID `{before.channel.id}`)\n**To:** `{after.channel.name}` (ID `{after.channel.id}`)\n**Time:** <t:{now_ts()}:F>"))
            view.add_item(c)
            await ch.send(view=view, allowed_mentions=NO_PING)
            return
        changes = []
        if before.mute != after.mute: changes.append(f"Server Mute: {before.mute} -> {after.mute}")
        if before.deaf != after.deaf: changes.append(f"Server Deaf: {before.deaf} -> {after.deaf}")
        if before.self_mute != after.self_mute: changes.append(f"Self Mute: {before.self_mute} -> {after.self_mute}")
        if before.self_deaf != after.self_deaf: changes.append(f"Self Deaf: {before.self_deaf} -> {after.self_deaf}")
        if before.self_stream != after.self_stream: changes.append(f"Streaming: {before.self_stream} -> {after.self_stream}")
        if before.self_video != after.self_video: changes.append(f"Camera: {before.self_video} -> {after.self_video}")
        if before.afk != after.afk: changes.append(f"AFK: {before.afk} -> {after.afk}")
        if changes:
            view = discord.ui.LayoutView()
            c = discord.ui.Container()
            c.add_item(discord.ui.TextDisplay(f"## VOICE STATE UPDATE"))
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            c.add_item(discord.ui.TextDisplay(f"**User:** `{member.display_name}` | ID `{member.id}`\n**Channel:** `{after.channel.name if after.channel else before.channel.name if before.channel else 'None'}`\n**Changes:** {', '.join(changes)}\n**Time:** <t:{now_ts()}:F>"))
            view.add_item(c)
            await ch.send(view=view, allowed_mentions=NO_PING)

    # ========== CHANNEL / THREAD / ROLE / EMOJI / INVITE / SERVER ==========
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        ch = self.get_ch(channel.guild, "logs_channel")
        if not ch: return
        mod, reason = await self.get_audit(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## CHANNEL CREATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Name:** `{channel.name}` | ID `{channel.id}`\n**Type:** `{channel.type}`\n**Category:** `{channel.category.name if channel.category else 'None'}`\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        ch = self.get_ch(channel.guild, "logs_channel")
        if not ch: return
        mod, reason = await self.get_audit(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## CHANNEL DELETED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Name:** `{channel.name}` | ID `{channel.id}`\n**Type:** `{channel.type}`\n**Category:** `{channel.category.name if hasattr(channel.category, 'name') and channel.category else 'None'}`\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        ch = self.get_ch(after.guild, "logs_channel")
        if not ch: return
        changes = []
        if before.name != after.name: changes.append(f"Name: `{before.name}` -> `{after.name}`")
        if getattr(before, 'topic', None) != getattr(after, 'topic', None): changes.append(f"Topic changed")
        if getattr(before, 'bitrate', None) != getattr(after, 'bitrate', None): changes.append(f"Bitrate: {getattr(before, 'bitrate', None)} -> {getattr(after, 'bitrate', None)}")
        if getattr(before, 'user_limit', None) != getattr(after, 'user_limit', None): changes.append(f"User Limit: {getattr(before, 'user_limit', None)} -> {getattr(after, 'user_limit', None)}")
        if not changes: return
        mod, reason = await self.get_audit(after.guild, discord.AuditLogAction.channel_update, after.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## CHANNEL UPDATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Channel:** `{after.name}` | ID `{after.id}`\n**Changes:** {', '.join(changes)}\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        ch = self.get_ch(thread.guild, "logs_thread")
        if not ch: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## THREAD CREATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Name:** `{thread.name}` | ID `{thread.id}`\n**Parent:** `{thread.parent.name if thread.parent else 'None'}`\n**Owner:** `{thread.owner.display_name if thread.owner else 'Unknown'}` | ID `{thread.owner_id}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        ch = self.get_ch(thread.guild, "logs_thread")
        if not ch: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## THREAD DELETED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Name:** `{thread.name}` | ID `{thread.id}`\n**Parent:** `{thread.parent.name if thread.parent else 'None'}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        ch = self.get_ch(role.guild, "logs_role")
        if not ch: return
        mod, reason = await self.get_audit(role.guild, discord.AuditLogAction.role_create, role.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## ROLE CREATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Role:** `{role.name}` | ID `{role.id}`\n**Color:** `{role.color}`\n**Hoist:** `{role.hoist}` | **Mentionable:** `{role.mentionable}` | **Managed:** `{role.managed}`\n**Perms Value:** `{role.permissions.value}`\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        ch = self.get_ch(role.guild, "logs_role")
        if not ch: return
        mod, reason = await self.get_audit(role.guild, discord.AuditLogAction.role_delete, role.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## ROLE DELETED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Role:** `{role.name}` | ID `{role.id}`\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        ch = self.get_ch(after.guild, "logs_role")
        if not ch: return
        changes = []
        if before.name != after.name: changes.append(f"Name: `{before.name}` -> `{after.name}`")
        if before.color != after.color: changes.append(f"Color: `{before.color}` -> `{after.color}`")
        if before.permissions != after.permissions: changes.append(f"Perms changed")
        if before.hoist != after.hoist: changes.append(f"Hoist: {before.hoist} -> {after.hoist}")
        if before.mentionable != after.mentionable: changes.append(f"Mentionable: {before.mentionable} -> {after.mentionable}")
        if not changes: return
        mod, reason = await self.get_audit(after.guild, discord.AuditLogAction.role_update, after.id)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## ROLE UPDATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Role:** `{after.name}` | ID `{after.id}`\n**Changes:** {', '.join(changes)}\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        ch = self.get_ch(invite.guild, "logs_invite")
        if not ch: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## INVITE CREATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Code:** `{invite.code}` | https://discord.gg/{invite.code}\n**Channel:** `{invite.channel.name}` | ID `{invite.channel.id}`\n**Creator:** `{invite.inviter.display_name if invite.inviter else 'Unknown'}` | ID `{invite.inviter.id if invite.inviter else 'Unknown'}`\n**Max Uses:** `{invite.max_uses or 'Unlimited'}` | **Max Age:** `{invite.max_age}s` | **Temporary:** `{invite.temporary}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        ch = self.get_ch(invite.guild, "logs_invite")
        if not ch: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## INVITE DELETED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Code:** `{invite.code}`\n**Channel:** `{invite.channel.name if hasattr(invite.channel, 'name') else 'Unknown'}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        ch = self.get_ch(guild, "logs_server")
        if not ch: return
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]
        if not added and not removed: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## EMOJIS UPDATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        if added:
            c.add_item(discord.ui.TextDisplay(f"**Added:** {', '.join([f'`{e.name}` (ID `{e.id}`)' for e in added])}"))
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        if removed:
            c.add_item(discord.ui.TextDisplay(f"**Removed:** {', '.join([f'`{e.name}` (ID `{e.id}`)' for e in removed])}"))
            c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        ch = self.get_ch(guild, "logs_server")
        if not ch: return
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## STICKERS UPDATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Before Count:** `{len(before)}` | **After Count:** `{len(after)}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        ch = self.get_ch(channel.guild, "logs_server")
        if not ch: return
        mod, reason = await self.get_audit(channel.guild, discord.AuditLogAction.webhook_create)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## WEBHOOKS UPDATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Channel:** `{channel.name}` | ID `{channel.id}`\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        ch = self.get_ch(after, "logs_server")
        if not ch: return
        changes = []
        if before.name != after.name: changes.append(f"Name: `{before.name}` -> `{after.name}`")
        if before.icon != after.icon: changes.append(f"Icon changed")
        if before.banner != after.banner: changes.append(f"Banner changed")
        if before.owner_id != after.owner_id: changes.append(f"Owner: {before.owner_id} -> {after.owner_id}")
        if not changes: return
        mod, reason = await self.get_audit(after, discord.AuditLogAction.guild_update)
        view = discord.ui.LayoutView()
        c = discord.ui.Container()
        c.add_item(discord.ui.TextDisplay(f"## SERVER UPDATED"))
        c.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        c.add_item(discord.ui.TextDisplay(f"**Changes:** {', '.join(changes)}\n**By:** {mod}\n**Reason:** `{reason}`\n**Time:** <t:{now_ts()}:F>"))
        view.add_item(c)
        await ch.send(view=view, allowed_mentions=NO_PING)





async def setup(bot):
    await bot.add_cog(LogsCog(bot))
