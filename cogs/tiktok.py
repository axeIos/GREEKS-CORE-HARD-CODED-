import asyncio
import json
import os
import re
from datetime import datetime, timezone
 
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
 
DATA_FILE = "data/tiktok.json"
CHECK_MINUTES = int(os.getenv("TIKTOK_INTERVAL", "5"))
PROXY = os.getenv("TIKTOK_PROXY")   # optional, e.g. http://user:pass@host:port
RSSHUB = os.getenv("RSSHUB_URL")    # optional, your own RSSHub instance
APIFY_TOKEN = os.getenv("APIFY_TOKEN")  # optional, most reliable source
UPDATE_HOURS = int(os.getenv("TIKTOK_UPDATE_HOURS", "24"))  # refresh stats every N hours
TRACK_DAYS = int(os.getenv("TIKTOK_TRACK_DAYS", "7"))       # keep refreshing for N days
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
 
 
def role_mention(guild_id: int, role_id: int) -> str:
    # the @everyone "role" has the same id as the guild
    return "@everyone" if role_id == guild_id else f"<@&{role_id}>"
 
 
class TikTokView(discord.ui.LayoutView):
    """Components V2 'embed' with separators and link buttons."""
 
    def __init__(self, username: str, video: dict, ping: str | None = None):
        super().__init__(timeout=None)
 
        vid_id = video["video_id"]
        url = f"https://www.tiktok.com/@{username}/video/{vid_id}"
        profile = f"https://www.tiktok.com/@{username}"
        title = (video.get("title") or "No title").strip()[:300]
        ts = int(video.get("create_time", datetime.now(timezone.utc).timestamp()))
 
        container = discord.ui.Container()
 
        if ping:
            container.add_item(discord.ui.TextDisplay(ping))
        container.add_item(
            discord.ui.TextDisplay(
                f"## <:372102690_TIKTOK_LOGO_1080:1564035875057438883> New TikTok from @{username}"
            )
        )
        container.add_item(
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
        )
 
        text = discord.ui.TextDisplay(f"**{title}**\n\n📅 Posted <t:{ts}:R>")
        cover = video.get("cover") or video.get("origin_cover")
        if cover:
            container.add_item(discord.ui.Section(text, accessory=discord.ui.Thumbnail(cover)))
        else:
            container.add_item(text)
 
        container.add_item(
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
        )
 
        stats = (
            f"❤️ {video.get('digg_count', 0):,}  •  "
            f"💬 {video.get('comment_count', 0):,}  •  "
            f"👁️ {video.get('play_count', 0):,}  •  "
            f"🔁 {video.get('share_count', 0):,}"
        )
        container.add_item(discord.ui.TextDisplay(stats))
 
        container.add_item(
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        )
 
        row = discord.ui.ActionRow()
        row.add_item(
            discord.ui.Button(label="Watch video", emoji="▶️", style=discord.ButtonStyle.link, url=url)
        )
        row.add_item(
            discord.ui.Button(label="Profile", emoji="👤", style=discord.ButtonStyle.link, url=profile)
        )
        container.add_item(row)
 
        self.add_item(container)
 
 
class TikTok(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        os.makedirs("data", exist_ok=True)
        self.data = self.load()
 
    # ---------- lifecycle ----------
    async def cog_load(self):
        self.session = aiohttp.ClientSession(headers=HEADERS)
        self.check_loop.start()
        self.update_loop.start()
 
    async def cog_unload(self):
        self.check_loop.cancel()
        self.update_loop.cancel()
        if self.session:
            await self.session.close()
 
    # ---------- storage ----------
    def load(self) -> dict:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
 
    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
 
    # ---------- fetch ----------
    # Every source returns a LIST of normalized videos. If one is blocked, the next is used.
    async def _get(self, url: str, **kw):
        async with self.session.get(
            url, proxy=PROXY, timeout=aiohttp.ClientTimeout(total=25), **kw
        ) as r:
            return r.status, await r.text()
 
    @staticmethod
    def _norm_web(it: dict) -> dict:
        """Normalize a TikTok web-JSON item."""
        st = it.get("stats") or {}
        vd = it.get("video") or {}
        vid = str(it["id"])
        return {
            "video_id": vid,
            "title": it.get("desc", ""),
            "cover": vd.get("cover") or vd.get("originCover") or it.get("cover"),
            "create_time": int(it.get("createTime") or (int(vid) >> 32)),
            "play_count": st.get("playCount", 0),
            "digg_count": st.get("diggCount", 0),
            "comment_count": st.get("commentCount", 0),
            "share_count": st.get("shareCount", 0),
        }
 
    @staticmethod
    def _walk(o, out: dict, strict: bool):
        if isinstance(o, dict):
            vid = str(o.get("id", ""))
            if vid.isdigit() and 15 <= len(vid) <= 20:
                if ("createTime" in o and "desc" in o) if strict else (
                    "desc" in o or "createTime" in o or "stats" in o
                ):
                    out[vid] = o
            for v in o.values():
                TikTok._walk(v, out, strict)
        elif isinstance(o, list):
            for v in o:
                TikTok._walk(v, out, strict)
 
    async def _src_profile(self, username: str) -> list[dict]:
        """Read the public profile page + official oEmbed."""
        status, html = await self._get(
            f"https://www.tiktok.com/@{username}",
            headers={**HEADERS, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"},
        )
        if "Just a moment" in html[:2000] or status in (403, 429):
            raise RuntimeError(f"TikTok profile blocked (HTTP {status})")
        if status == 404:
            raise RuntimeError("Account does not exist")
 
        m = re.search(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S
        )
        if m:
            try:
                found: dict = {}
                self._walk(json.loads(m.group(1)), found, strict=True)
                if found:
                    return [self._norm_web(i) for i in found.values()]
            except Exception as e:
                print(f"[TikTok] json parse failed: {e}")
 
        ids = re.findall(rf"/@{re.escape(username)}/video/(\d{{15,20}})", html, re.I)
        if not ids:
            raise RuntimeError("No videos found on profile page (private/empty/blocked)")
        vid = str(max(int(i) for i in ids))
        video = {"video_id": vid, "title": "", "cover": None, "create_time": int(vid) >> 32}
        try:
            s2, body = await self._get(
                "https://www.tiktok.com/oembed",
                params={"url": f"https://www.tiktok.com/@{username}/video/{vid}"},
            )
            js = json.loads(body)
            video["title"] = js.get("title", "")
            video["cover"] = js.get("thumbnail_url")
        except Exception as e:
            print(f"[TikTok] oembed failed: {e}")
        return [video]
 
    async def _src_tikwm(self, username: str) -> list[dict]:
        status, raw = await self._get(
            "https://www.tikwm.com/api/user/posts",
            params={"unique_id": username, "count": 10, "cursor": 0},
            headers=HEADERS,
        )
        try:
            js = json.loads(raw)
        except json.JSONDecodeError:
            raise RuntimeError(f"tikwm blocked (HTTP {status})")
        if js.get("code") != 0:
            raise RuntimeError(f"tikwm error: {js.get('msg')}")
        videos = (js.get("data") or {}).get("videos") or []
        if not videos:
            raise RuntimeError("tikwm: no videos")
        return [
            {**v, "video_id": str(v["video_id"])} for v in videos
        ]
 
    async def _src_rsshub(self, username: str) -> list[dict]:
        if not RSSHUB:
            raise RuntimeError("RSSHub not configured")
        status, xml = await self._get(f"{RSSHUB.rstrip('/')}/tiktok/user/@{username}")
        ids = set(re.findall(r"/video/(\d{15,20})", xml))
        if not ids:
            raise RuntimeError(f"RSSHub returned nothing (HTTP {status})")
        return [
            {"video_id": i, "title": "", "cover": None, "create_time": int(i) >> 32}
            for i in ids
        ]
 
    async def _src_embed(self, username: str) -> list[dict]:
        """TikTok public embed page of a profile."""
        status, html = await self._get(
            f"https://www.tiktok.com/embed/@{username}",
            headers={**HEADERS, "Accept": "text/html"},
        )
        if status != 200 or "Just a moment" in html[:2000]:
            raise RuntimeError(f"embed blocked (HTTP {status})")
        found: dict = {}
        for m in re.finditer(r"<script[^>]*>(\{.*?\})</script>", html, re.S):
            try:
                self._walk(json.loads(m.group(1)), found, strict=False)
            except Exception:
                continue
        if not found:
            raise RuntimeError("embed page has no video list")
        return [self._norm_web(i) for i in found.values()]
 
    async def _src_apify(self, username: str) -> list[dict]:
        """Apify TikTok scraper (needs APIFY_TOKEN). Works from any host."""
        if not APIFY_TOKEN:
            raise RuntimeError("APIFY_TOKEN not set")
        url = (
            "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/"
            f"run-sync-get-dataset-items?token={APIFY_TOKEN}"
        )
        payload = {
            "profiles": [username],
            "resultsPerPage": 5,
            "profileSorting": "latest",
            "excludePinnedPosts": True,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }
        async with self.session.post(
            url, json=payload, timeout=aiohttp.ClientTimeout(total=150)
        ) as r:
            status = r.status
            body = await r.text()
        if status not in (200, 201):
            raise RuntimeError(f"apify HTTP {status}: {body[:150]}")
        items = [i for i in json.loads(body) if i.get("id")]
        if not items:
            raise RuntimeError("apify returned no videos")
        out = []
        for it in items:
            meta = it.get("videoMeta") or {}
            out.append({
                "video_id": str(it["id"]),
                "title": it.get("text", ""),
                "cover": meta.get("coverUrl") or meta.get("originalCoverUrl"),
                "create_time": int(it.get("createTime", 0)),
                "play_count": it.get("playCount", 0),
                "digg_count": it.get("diggCount", 0),
                "comment_count": it.get("commentCount", 0),
                "share_count": it.get("shareCount", 0),
            })
        return out
 
    async def fetch_videos(self, username: str) -> tuple[list[dict] | None, str | None]:
        """Returns (videos, error_message). Tries every source until one works."""
        errors = []
        sources = []
        if APIFY_TOKEN:
            sources.append(("apify", self._src_apify))
        sources += [
            ("embed", self._src_embed),
            ("profile", self._src_profile),
            ("tikwm", self._src_tikwm),
        ]
        if RSSHUB:
            sources.append(("rsshub", self._src_rsshub))
        for name, fn in sources:
            try:
                videos = await fn(username)
                if videos:
                    return videos, None
            except Exception as e:
                msg = f"{name}: {e}"
                errors.append(msg)
                print(f"[TikTok] {username} -> {msg}")
            await asyncio.sleep(1)
        return None, " | ".join(errors)[:900]
 
    async def fetch_latest(self, username: str) -> tuple[dict | None, str | None]:
        videos, err = await self.fetch_videos(username)
        if not videos:
            return None, err
        return max(videos, key=lambda v: v.get("create_time", 0)), None
 
    # ---------- stats tracking ----------
    def track(self, guild_id, username, channel_id, message_id, ping, video):
        now = int(datetime.now(timezone.utc).timestamp())
        g = self.data.setdefault(str(guild_id), {"accounts": {}})
        g.setdefault("tracked", []).append({
            "username": username,
            "channel_id": channel_id,
            "message_id": message_id,
            "ping": ping,
            "video": video,
            "posted_at": now,
            "last_update": now,
        })
        self.save()
 
    @tasks.loop(minutes=30)
    async def update_loop(self):
        now = int(datetime.now(timezone.utc).timestamp())
        for gdata in list(self.data.values()):
            keep = []
            for t in gdata.get("tracked", []):
                if now - t["posted_at"] > TRACK_DAYS * 86400:
                    continue  # stop tracking old posts
                if now - t["last_update"] < UPDATE_HOURS * 3600:
                    keep.append(t)
                    continue
 
                videos, err = await self.fetch_videos(t["username"])
                await asyncio.sleep(2)
                fresh = next(
                    (v for v in (videos or []) if str(v["video_id"]) == str(t["video"]["video_id"])),
                    None,
                )
                if fresh is None:
                    # not found right now -> retry in about 1 hour
                    t["last_update"] = now - UPDATE_HOURS * 3600 + 3600
                    keep.append(t)
                    continue
 
                # keep old title/cover if the source did not provide them
                merged = {**t["video"], **{k: v for k, v in fresh.items() if v not in (None, "")}}
                channel = self.bot.get_channel(t["channel_id"])
                if channel is None:
                    keep.append(t)
                    continue
                try:
                    await channel.get_partial_message(t["message_id"]).edit(
                        view=TikTokView(t["username"], merged, t.get("ping")),
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                    t["video"] = merged
                    t["last_update"] = now
                    keep.append(t)
                    print(f"[TikTok] updated stats for @{t['username']} ({merged['video_id']})")
                except discord.NotFound:
                    pass  # message deleted -> drop it
                except discord.HTTPException as e:
                    print(f"[TikTok] edit error: {e}")
                    keep.append(t)
            gdata["tracked"] = keep
        self.save()
 
    @update_loop.before_loop
    async def before_update_loop(self):
        await self.bot.wait_until_ready()
 
    # ---------- loop ----------
    @tasks.loop(minutes=CHECK_MINUTES)
    async def check_loop(self):
        for guild_id, gdata in list(self.data.items()):
            for username, info in list(gdata.get("accounts", {}).items()):
                video, err = await self.fetch_latest(username)
                await asyncio.sleep(2)
                if not video:
                    continue
 
                vid_id = str(video["video_id"])
                if vid_id == info.get("last_id"):
                    print(f"[TikTok] @{username}: no new video (latest {vid_id})")
                    continue
                if video.get("create_time", 0) <= info.get("last_time", 0):
                    continue
 
                channel = self.bot.get_channel(info["channel_id"])
                if channel is None:
                    continue
 
                ping = role_mention(channel.guild.id, info["role_id"]) if info.get("role_id") else None
                try:
                    msg = await channel.send(
                        view=TikTokView(username, video, ping),
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                    )
                    self.track(channel.guild.id, username, channel.id, msg.id, ping, video)
                    info["last_id"] = vid_id
                    info["last_time"] = video.get("create_time", 0)
                    self.save()
                except discord.HTTPException as e:
                    print(f"[TikTok] send error: {e}")
 
    @check_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
 
    # ---------- commands ----------
    group = app_commands.Group(
        name="tiktok",
        description="TikTok notifications",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )
 
    @group.command(name="add", description="Add a TikTok account for notifications")
    @app_commands.describe(
        username="The TikTok username (without @)",
        channel="Channel where notifications will be sent",
        role="(Optional) Role to ping",
        post_latest="Also post the current latest video right now",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        username: str,
        channel: discord.TextChannel,
        role: discord.Role | None = None,
        post_latest: bool = False,
    ):
        await interaction.response.defer(ephemeral=True)
        username = username.lstrip("@").strip().lower()
 
        video, err = await self.fetch_latest(username)
        if video is None:
            return await interaction.followup.send(
                f"❌ Could not fetch **@{username}**.\n**Reason:** {err}"
            )
 
        g = self.data.setdefault(str(interaction.guild_id), {"accounts": {}})
        g["accounts"][username] = {
            "channel_id": channel.id,
            "role_id": role.id if role else None,
            "last_id": str(video["video_id"]),
            "last_time": video.get("create_time", 0),
        }
        self.save()
        if post_latest:
            ping = role_mention(interaction.guild_id, role.id) if role else None
            msg = await channel.send(
                view=TikTokView(username, video, ping),
                allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
            )
            self.track(interaction.guild_id, username, channel.id, msg.id, ping, video)
        await interaction.followup.send(
            f"✅ I will post new TikToks from **@{username}** in {channel.mention}."
        )
 
    @group.command(name="remove", description="Remove a TikTok account")
    async def remove(self, interaction: discord.Interaction, username: str):
        username = username.lstrip("@").strip().lower()
        accounts = self.data.get(str(interaction.guild_id), {}).get("accounts", {})
        if username in accounts:
            del accounts[username]
            self.save()
            await interaction.response.send_message(f"🗑️ Removed **@{username}**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ That account is not being tracked.", ephemeral=True)
 
    @group.command(name="list", description="List tracked TikTok accounts")
    async def list_accounts(self, interaction: discord.Interaction):
        accounts = self.data.get(str(interaction.guild_id), {}).get("accounts", {})
        if not accounts:
            return await interaction.response.send_message("No accounts are being tracked.", ephemeral=True)
        lines = [f"• **@{u}** → <#{i['channel_id']}>" for u, i in accounts.items()]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)
 
    @group.command(name="test", description="Send a test notification")
    async def test(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(ephemeral=True)
        username = username.lstrip("@").strip().lower()
        video, err = await self.fetch_latest(username)
        if not video:
            return await interaction.followup.send(f"❌ Failed.\n**Reason:** {err}")
        await interaction.channel.send(view=TikTokView(username, video))
        await interaction.followup.send("✅ Sent.")
 
 
async def setup(bot: commands.Bot):
    await bot.add_cog(TikTok(bot))
 