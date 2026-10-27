import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

load_dotenv(override=False)
TOKEN = (os.getenv("BOT_TOKEN") or os.getenv("TOKEN") or "").strip()
GUILD_ID = (os.getenv("GUILD_ID") or "").strip()

# Fallback hardcoded guild ID - PUT YOUR SERVER ID HERE IF ENV DOESNT WORK
HARDCODED_GUILD_ID = 0

try:
    GUILD_ID_INT = int(GUILD_ID) if GUILD_ID and GUILD_ID.isdigit() else HARDCODED_GUILD_ID
except:
    GUILD_ID_INT = HARDCODED_GUILD_ID

# FIXED INTENTS - Added voice_states for TTS
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.presences = True
intents.guild_messages = True
intents.voice_states = True  # FIX FOR TTS - REQUIRED
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"========================================")
    print(f"✅ GREEKS Bot online as {bot.user}")
    print(f"ID: {bot.user.id}")
    print(f"Guilds: {len(bot.guilds)}")
    print(f"Presences intent: {bot.intents.presences} | Members intent: {bot.intents.members} | Voice intent: {bot.intents.voice_states}")
    print(f"========================================")
    for g in bot.guilds:
        print(f"  {g.name} ({g.id}) - {g.member_count} members - chunked={g.chunked}")

    # Sync commands to guild for instant appearance
    try:
        if GUILD_ID_INT:
            guild_obj = discord.Object(id=GUILD_ID_INT)
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"✅ Synced {len(synced)} commands to guild {GUILD_ID_INT}")
        else:
            for g in bot.guilds:
                bot.tree.copy_global_to(guild=g)
                synced = await bot.tree.sync(guild=g)
                print(f"✅ Synced {len(synced)} to {g.name}")
    except Exception as e:
        print(f"Sync error: {e}")
        import traceback
        traceback.print_exc()

@bot.event
async def setup_hook():
    # Clear global commands to avoid 100 limit
    bot.tree.clear_commands(guild=None)
    try:
        await bot.tree.sync()
        print("✅ Cleared global commands")
    except Exception as e:
        print(f"Clear error (ok first time): {e}")

    print("Loading cogs...")
    if not os.path.exists("./cogs"):
        print("No cogs folder found")
        return

    for f in os.listdir("./cogs"):
        if not f.endswith(".py"):
            continue
        if f.startswith("__"):
            continue
        if "_backup" in f or "backup" in f or f == "weel.py":
            print(f"  Skipping {f}")
            continue
        try:
            await bot.load_extension(f"cogs.{f[:-3]}")
            print(f"  Loaded {f}")
        except Exception as e:
            print(f"  Failed {f}: {e}")
            import traceback
            traceback.print_exc()

    print(f"Total commands in tree: {len(bot.tree.get_commands())}")

@bot.command(name="sync")
@commands.is_owner()
async def sync_cmd(ctx):
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        names = ", ".join([c.name for c in synced])[:1500]
        await ctx.send(f"✅ Synced {len(synced)} commands\n{names}\n\nDo Ctrl+R in Discord")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="sync_global_clear")
@commands.is_owner()
async def sync_global_clear(ctx):
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    await ctx.send("✅ Cleared global commands. Now do !sync")

@bot.command(name="status")
@commands.is_owner()
async def status_cmd(ctx):
    cfg_text = f"Presences: {bot.intents.presences}\nMembers: {bot.intents.members}\nVoice: {bot.intents.voice_states}\nGuilds: {len(bot.guilds)}\nCommands: {len(bot.tree.get_commands())}"
    await ctx.send(f"```{cfg_text}```")

async def main():
    if not TOKEN:
        print("ERROR: No BOT_TOKEN in .env")
        return
    try:
        async with bot:
            await bot.start(TOKEN)
    except asyncio.CancelledError:
        print("Bot shutdown")
    except KeyboardInterrupt:
        print("Stopped by user")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown complete")