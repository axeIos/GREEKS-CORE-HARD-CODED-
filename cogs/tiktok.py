import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import asyncio
import aiohttp
import re
from datetime import datetime

DATA_FILE = "tiktok_data.json"
TIKTOK_EMOJI = "<:372102690_TIKTOK_LOGO_1080:1564035875057438883>"

class TikTokNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self.load_data()
        self.session = None
        print(f"[TikTok] Loaded - NO CLOUDFLARE - secUid API + INSANE CLEAN")
        self.check_tiktok.start()

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            return {"guilds": {}}
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"guilds": {}}

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def get_guild_data(self, guild_id):
        gid = str(guild_id)
        if gid not in self.data["guilds"]:
            self.data["guilds"][gid] = {"channel_id": None, "users": {}}
        return self.data["guilds"][gid]

    async def get_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    def create_insane_clean_message(self, username, display_name, video_url):
        """INSANE CLEAN - Only latest video, button inside"""
        try:
            view = discord.ui.LayoutView()
            container = discord.ui.Container()
            
            container.add_item(discord.ui.TextDisplay(f"## {TIKTOK_EMOJI} @{username} just uploaded!"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large, divider=False))
            container.add_item(discord.ui.TextDisplay(f"**{display_name}** • `@{username}`"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=True))
            container.add_item(discord.ui.TextDisplay(f"{video_url}"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large, divider=False))
            
            action_row = discord.ui.ActionRow()
            action_row.add_item(discord.ui.Button(label="Watch on TikTok", style=discord.ButtonStyle.link, url=video_url))
            container.add_item(action_row)
            
            view.add_item(container)
            return view
        except Exception as e:
            print(f"[TikTok] Clean error: {e}")
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="Watch on TikTok", style=discord.ButtonStyle.link, url=video_url))
            return view

    async def fetch_with_secuid_api(self, username, session):
        """Use secUid extraction + TikTok internal API - bypasses block without Cloudflare"""
        try:
            print(f"[TikTok] Trying secUid API for @{username}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"https://www.tiktok.com/@{username}",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            # Step 1: Get page even if blocked - it may still contain secUid
            try:
                async with session.get(f"https://www.tiktok.com/@{username}", headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    text = await resp.text()
                    print(f"[TikTok] Page len {len(text)} for @{username} - looking for secUid")
                    
                    # Extract secUid - even blocked page has it
                    secuid_match = re.search(r'"secUid":"([^"]+)"', text)
                    if secuid_match:
                        secUid = secuid_match.group(1)
                        print(f"[TikTok] Found secUid for @{username}: {secUid[:20]}...")
                        
                        # Step 2: Use secUid to get videos via TikTok API
                        # This API is less blocked than main page
                        api_headers = {
                            "User-Agent": headers["User-Agent"],
                            "Referer": f"https://www.tiktok.com/@{username}",
                            "Accept": "application/json",
                        }
                        
                        # Try multiple API endpoints with secUid
                        api_urls = [
                            f"https://www.tiktok.com/api/post/item_list/?aid=1988&app_language=en&app_name=tiktok_web&battery_info=1&browser_language=en-US&browser_name=Mozilla&browser_online=true&browser_platform=Win32&browser_version=5.0&channel=tiktok_web&cookie_enabled=true&count=1&cursor=0&device_brand=&device_id=0&device_model=&device_platform=web_pc&focus_state=false&from_page=user&history_len=2&is_fullscreen=false&is_page_visible=true&os=windows&priority_region=&referer=&region=US&screen_height=1080&screen_width=1920&secUid={secUid}&tz_name=America%2FNew_York&uniqueId={username}&webcast_language=en",
                            f"https://m.tiktok.com/api/post/item_list/?aid=1988&count=1&cursor=0&secUid={secUid}&from_page=user&uniqueId={username}",
                        ]
                        
                        for api_url in api_urls:
                            try:
                                async with session.get(api_url, headers=api_headers, timeout=aiohttp.ClientTimeout(total=15)) as api_resp:
                                    print(f"[TikTok] API status {api_resp.status} for @{username} via secUid")
                                    if api_resp.status == 200:
                                        try:
                                            data = await api_resp.json()
                                            if "itemList" in data and data["itemList"]:
                                                vid = str(data["itemList"][0].get("id", ""))
                                                if vid and len(vid) >= 10:
                                                    print(f"[TikTok] secUid API SUCCESS @{username}: {vid}")
                                                    return vid, f"https://www.tiktok.com/@{username}/video/{vid}"
                                            # Also try other formats
                                            text_data = json.dumps(data)
                                            vids = re.findall(r'"id"\s*:\s*"?\s*(\d{19})', text_data)
                                            if vids:
                                                print(f"[TikTok] secUid regex SUCCESS @{username}: {vids[0]}")
                                                return vids[0], f"https://www.tiktok.com/@{username}/video/{vids[0]}"
                                        except Exception as e:
                                            print(f"[TikTok] secUid API JSON error: {e}")
                                            # Try as text
                                            try:
                                                txt = await api_resp.text()
                                                vids = re.findall(r'(\d{19})', txt)
                                                for v in vids:
                                                    if v.startswith('7') and len(v) == 19:
                                                        print(f"[TikTok] secUid text SUCCESS @{username}: {v}")
                                                        return v, f"https://www.tiktok.com/@{username}/video/{v}"
                                            except:
                                                pass
                            except Exception as e:
                                print(f"[TikTok] secUid API url error: {e}")
                                continue
                    
                    # Fallback: Try to find video ID directly in page even if blocked
                    # Sometimes page has video IDs even when SIGI_STATE is empty
                    vids = re.findall(r'/video/(\d{19})', text)
                    if vids:
                        # Filter unique
                        seen = []
                        for v in vids:
                            if v not in seen:
                                seen.append(v)
                        if seen:
                            print(f"[TikTok] Direct page video SUCCESS @{username}: {seen[0]}")
                            return seen[0], f"https://www.tiktok.com/@{username}/video/{seen[0]}"
                    
                    print(f"[TikTok] No secUid or video found in page for @{username}")
            except Exception as e:
                print(f"[TikTok] secUid page fetch error @{username}: {e}")
            
            # Method 2: Try TikTok webapp API without secUid
            try:
                print(f"[TikTok] Trying webapp API without secUid for @{username}")
                api_url = f"https://www.tiktok.com/api/user/detail/?aid=1988&app_language=en&uniqueId={username}"
                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    print(f"[TikTok] user/detail status {resp.status} for @{username}")
                    if resp.status == 200:
                        try:
                            data = await resp.json()
                            text = json.dumps(data)
                            # Extract secUid from here too
                            sec_match = re.search(r'"secUid"\s*:\s*"([^"]+)"', text)
                            if sec_match:
                                secUid = sec_match.group(1)
                                # Retry with secUid
                                item_url = f"https://www.tiktok.com/api/post/item_list/?aid=1988&count=1&secUid={secUid}&from_page=user&uniqueId={username}"
                                async with session.get(item_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as item_resp:
                                    if item_resp.status == 200:
                                        item_data = await item_resp.json()
                                        if "itemList" in item_data and item_data["itemList"]:
                                            vid = str(item_data["itemList"][0].get("id", ""))
                                            if vid:
                                                print(f"[TikTok] user/detail -> item_list SUCCESS @{username}: {vid}")
                                                return vid, f"https://www.tiktok.com/@{username}/video/{vid}"
                        except Exception as e:
                            print(f"[TikTok] user/detail error: {e}")
            except Exception as e:
                print(f"[TikTok] user/detail fetch error: {e}")
            
            return None, None
        except Exception as e:
            print(f"[TikTok] secUid method error @{username}: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    async def fetch_tiktok_info(self, username):
        """Only latest video - secUid method, no Cloudflare, no yt-dlp"""
        username = username.replace('@','').strip().lower()
        if not username:
            return None
        session = await self.get_session()
        display_name = username
        last_video_id = "0"
        last_video_url = f"https://www.tiktok.com/@{username}"
        user_exists = False
        
        try:
            url = f"https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{username}"
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("author_name"):
                        display_name = data.get("author_name")
                        user_exists = True
                        print(f"[TikTok] oEmbed SUCCESS @{username}: {display_name}")
        except Exception as e:
            print(f"[TikTok] oEmbed error: {e}")

        if not user_exists:
            return None

        # Try secUid API - bypasses block without Cloudflare
        vid, vurl = await self.fetch_with_secuid_api(username, session)
        if vid:
            last_video_id = vid
            last_video_url = vurl

        print(f"[TikTok] FINAL @{username}: video={last_video_id}")
        return {"username": username, "display_name": display_name, "last_video_id": last_video_id, "last_video_url": last_video_url}

    @tasks.loop(minutes=2)
    async def check_tiktok(self):
        if not self.data["guilds"]:
            return
        for gid_str, gdata in list(self.data["guilds"].items()):
            cid = gdata.get("channel_id")
            if not cid:
                continue
            guild = self.bot.get_guild(int(gid_str))
            if not guild:
                continue
            channel = guild.get_channel(cid)
            if not channel:
                continue
            for uname, tracked in list(gdata.get("users", {}).items()):
                try:
                    info = await self.fetch_tiktok_info(uname)
                    if not info:
                        continue
                    old_vid = tracked.get("last_video_id", "0")
                    new_vid = info.get("last_video_id", "0")
                    print(f"[TikTok] Check @{uname}: old={old_vid} new={new_vid}")
                    
                    if new_vid != "0" and new_vid != old_vid:
                        try:
                            view = self.create_insane_clean_message(uname, info['display_name'], info['last_video_url'])
                            if isinstance(view, tuple):
                                v, embed = view
                                if embed:
                                    await channel.send(embed=embed, view=v)
                                else:
                                    await channel.send(view=v)
                            else:
                                await channel.send(view=view)
                            print(f"[TikTok] SENT LATEST @{uname}: {new_vid}")
                        except Exception as e:
                            print(f"[TikTok] Send error: {e}")
                    
                    if new_vid != "0":
                        self.data["guilds"][gid_str]["users"][uname]["last_video_id"] = new_vid
                        self.data["guilds"][gid_str]["users"][uname]["last_check"] = datetime.now().isoformat()
                        self.save_data()
                    
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"[TikTok] Loop error {uname}: {e}")
                    continue

    @check_tiktok.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()
        print("[TikTok] Ready - secUid API + Insane Clean - Latest only - No Cloudflare")

    def cog_unload(self):
        self.check_tiktok.cancel()
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())

    @commands.hybrid_group(name="tiktok", description="Manage TikTok notifications")
    async def tiktok_group(self, ctx):
        if ctx.invoked_subcommand is None:
            try:
                view = discord.ui.LayoutView()
                container = discord.ui.Container()
                container.add_item(discord.ui.TextDisplay(f"## {TIKTOK_EMOJI} TikTok"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=True))
                container.add_item(discord.ui.TextDisplay("`/tiktok channel #channel`\n`/tiktok add @username`\n`/tiktok remove @username`\n`/tiktok list`"))
                view.add_item(container)
                await ctx.send(view=view, ephemeral=True)
            except:
                await ctx.send(f"{TIKTOK_EMOJI} TikTok", ephemeral=True)

    @tiktok_group.command(name="channel", description="Set notification channel")
    @app_commands.describe(channel="Channel for TikTok alerts")
    async def set_channel(self, ctx, channel: discord.TextChannel):
        guild_data = self.get_guild_data(ctx.guild.id)
        guild_data["channel_id"] = channel.id
        self.save_data()
        try:
            view = discord.ui.LayoutView()
            container = discord.ui.Container()
            container.add_item(discord.ui.TextDisplay(f"## {TIKTOK_EMOJI} Channel Set"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=True))
            container.add_item(discord.ui.TextDisplay(f"→ {channel.mention}"))
            view.add_item(container)
            await ctx.send(view=view, ephemeral=True)
        except:
            await ctx.send(f"Channel set to {channel.mention}", ephemeral=True)

    @tiktok_group.command(name="add", description="Add a TikTok creator")
    @app_commands.describe(username="TikTok username")
    async def add_user(self, ctx, username: str):
        try:
            await ctx.defer(ephemeral=True)
            deferred = True
        except:
            deferred = False
        clean_name = username.replace('@','').strip().lower()
        guild_data = self.get_guild_data(ctx.guild.id)
        if len(guild_data["users"]) >= 25:
            msg = "Max 25 creators"
            if deferred:
                try: await ctx.followup.send(msg, ephemeral=True)
                except: await ctx.send(msg, ephemeral=True)
            else: await ctx.send(msg, ephemeral=True)
            return
        if clean_name.lower() in [u.lower() for u in guild_data["users"].keys()]:
            msg = f"@{clean_name} already tracked"
            if deferred:
                try: await ctx.followup.send(msg, ephemeral=True)
                except: await ctx.send(msg, ephemeral=True)
            else: await ctx.send(msg, ephemeral=True)
            return
        if not guild_data.get("channel_id"):
            msg = "Set channel first: /tiktok channel #channel"
            if deferred:
                try: await ctx.followup.send(msg, ephemeral=True)
                except: await ctx.send(msg, ephemeral=True)
            else: await ctx.send(msg, ephemeral=True)
            return
        try:
            info = await asyncio.wait_for(self.fetch_tiktok_info(clean_name), timeout=40)
        except:
            info = None
        
        guild_data["users"][clean_name] = {"last_video_id": info.get("last_video_id") or "0" if info else "0", "added_by": ctx.author.id, "added_at": datetime.now().isoformat(), "last_check": datetime.now().isoformat()}
        self.save_data()
        
        try:
            view = discord.ui.LayoutView()
            container = discord.ui.Container()
            container.add_item(discord.ui.TextDisplay(f"## {TIKTOK_EMOJI} Tracking @{clean_name}"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=True))
            if info and info.get("last_video_id") != "0":
                container.add_item(discord.ui.TextDisplay(f"Latest: `{info.get('last_video_id')[:10]}...`\nOnly latest will be sent"))
            else:
                container.add_item(discord.ui.TextDisplay(f"Watching for uploads\nOnly latest video will be sent"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=False))
            action_row = discord.ui.ActionRow()
            action_row.add_item(discord.ui.Button(label="Profile", style=discord.ButtonStyle.link, url=f"https://www.tiktok.com/@{clean_name}"))
            container.add_item(action_row)
            view.add_item(container)
            if deferred:
                try: await ctx.followup.send(view=view, ephemeral=True)
                except: await ctx.send(view=view, ephemeral=True)
            else: await ctx.send(view=view, ephemeral=True)
        except:
            if deferred:
                try: await ctx.followup.send(f"Tracking @{clean_name}", ephemeral=True)
                except: await ctx.send(f"Tracking @{clean_name}", ephemeral=True)
            else: await ctx.send(f"Tracking @{clean_name}", ephemeral=True)

    @tiktok_group.command(name="remove", description="Remove a tracked creator")
    @app_commands.describe(username="Username to remove")
    async def remove_user(self, ctx, username: str):
        clean_name = username.replace('@','').strip().lower()
        guild_data = self.get_guild_data(ctx.guild.id)
        found = None
        for key in guild_data["users"].keys():
            if key.lower() == clean_name.lower():
                found = key
                break
        if not found:
            return await ctx.send(f"@{clean_name} not tracked.", ephemeral=True)
        del guild_data["users"][found]
        self.save_data()
        await ctx.send(f"Removed @{found}", ephemeral=True)

    @tiktok_group.command(name="list", description="View tracked creators")
    async def list_users(self, ctx):
        guild_data = self.get_guild_data(ctx.guild.id)
        users = guild_data.get("users", {})
        if not users:
            try:
                view = discord.ui.LayoutView()
                container = discord.ui.Container()
                container.add_item(discord.ui.TextDisplay(f"## {TIKTOK_EMOJI} Tracked"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=True))
                container.add_item(discord.ui.TextDisplay("No creators yet."))
                view.add_item(container)
                await ctx.send(view=view, ephemeral=True)
            except:
                await ctx.send("No creators tracked.", ephemeral=True)
            return
        
        try:
            view = discord.ui.LayoutView()
            container = discord.ui.Container()
            container.add_item(discord.ui.TextDisplay(f"## {TIKTOK_EMOJI} Tracked ({len(users)})"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=True))
            desc = ""
            for i, (u, data) in enumerate(users.items(), 1):
                vid = data.get("last_video_id", "0")
                status = "watching" if vid == "0" else "active"
                desc += f"`{i}.` **@{u}** • {status}\n"
            container.add_item(discord.ui.TextDisplay(desc))
            view.add_item(container)
            await ctx.send(view=view, ephemeral=True)
        except:
            await ctx.send(f"Tracked: {', '.join(users.keys())}", ephemeral=True)

    @tiktok_group.command(name="debug", description="Debug TikTok API")
    @app_commands.describe(username="Username to debug")
    async def debug_user(self, ctx, username: str):
        await ctx.defer(ephemeral=True)
        clean_name = username.replace('@','').strip()
        info = await self.fetch_tiktok_info(clean_name)
        if info:
            try:
                view = discord.ui.LayoutView()
                container = discord.ui.Container()
                container.add_item(discord.ui.TextDisplay(f"## {TIKTOK_EMOJI} @{info['username']}"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=True))
                has_vid = "latest only" if info['last_video_id'] != "0" else "no videos - blocked"
                container.add_item(discord.ui.TextDisplay(f"**{info['display_name']}**\nID: `{info['last_video_id']}`\n{has_vid}"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, divider=False))
                action_row = discord.ui.ActionRow()
                action_row.add_item(discord.ui.Button(label="Profile", style=discord.ButtonStyle.link, url=f"https://www.tiktok.com/@{info['username']}"))
                if info['last_video_id'] != "0":
                    action_row.add_item(discord.ui.Button(label="Watch", style=discord.ButtonStyle.link, url=info['last_video_url']))
                container.add_item(action_row)
                view.add_item(container)
                await ctx.followup.send(view=view, ephemeral=True)
            except:
                await ctx.followup.send(f"@{info['username']}: {info['last_video_id']}", ephemeral=True)
        else:
            await ctx.followup.send(f"Could not find @{clean_name}", ephemeral=True)

async def setup(bot):
    for cmd in ['tiktok']:
        if bot.get_command(cmd): bot.remove_command(cmd)
        try: bot.tree.remove_command(cmd)
        except: pass
    await bot.add_cog(TikTokNotify(bot))
