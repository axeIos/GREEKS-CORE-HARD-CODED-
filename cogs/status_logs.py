
import discord
from discord.ext import commands, tasks
from utils.helpers import load_config, make_v2_logs_embed
class StatusLogsCog(commands.Cog):
    def __init__(self, bot): self.bot=bot; self.status_loop.start()
    @tasks.loop(seconds=300)
    async def status_loop(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try: await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"Over {guild.member_count} Members"))
            except: pass
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot: return
        cfg=load_config()
        ch_id=cfg["channels"].get("logs")
        if not ch_id: return
        ch=message.guild.get_channel(ch_id)
        if not ch: return
        await ch.send(view=make_v2_logs_embed("Message Deleted", f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content[:1000]}", color=0xED4245))
    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg=load_config()
        ch_id=cfg["channels"].get("logs")
        if not ch_id: return
        ch=member.guild.get_channel(ch_id)
        if ch: await ch.send(view=make_v2_logs_embed("Member Joined", f"{member.mention} joined - {member.guild.member_count} members", color=0x57F287))
async def setup(bot): await bot.add_cog(StatusLogsCog(bot))
