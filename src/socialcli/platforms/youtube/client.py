"""
YouTube platform client — browser automation.

Login: Google login via browser
Publish: Playwright via studio.youtube.com
Search: youtube.com search scraping
"""
from __future__ import annotations
from typing import List
import click, httpx
from socialcli.platforms.base import *
from socialcli.auth.cookie_store import load_cookies, cookie_string, load_account_info
from socialcli.auth.browser_login import browser_login

DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

class YoutubePlatform(Platform):
    name = "youtube"
    display_name = "YouTube"
    icon = "▶️"
    LOGIN_URL = "https://accounts.google.com/signin/v2/identifier?service=youtube"
    SUCCESS_URL = "youtube.com"

    def login(self, account="default", **kw):
        return browser_login(self.name, self.LOGIN_URL, self.SUCCESS_URL, account, kw.get("headless", False))

    def check_login(self, account="default"):
        cookies = load_cookies(self.name, account)
        return bool(cookies and len(cookies) > 3)

    def _headers(self, account="default"):
        return {"User-Agent": DEFAULT_UA, "Cookie": cookie_string(self.name, account), "Referer": "https://www.youtube.com/"}

    def publish(self, content: Content, account="default") -> PublishResult:
        if not content.video:
            return PublishResult(success=False, platform=self.name, error="YouTube requires a video")
        try:
            from socialcli.platforms.youtube.browser import youtube_publish
            return youtube_publish(content, account)
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query, account="default", **kw) -> List[SearchResult]:
        headers = self._headers(account)
        try:
            resp = httpx.get(f"https://www.youtube.com/results?search_query={query}", headers=headers, timeout=15)
            results = []
            if resp.status_code == 200:
                import re, json
                match = re.search(r'var ytInitialData = ({.*?});', resp.text)
                if match:
                    data = json.loads(match.group(1))
                    contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
                    for section in contents:
                        for item in section.get("itemSectionRenderer", {}).get("contents", []):
                            video = item.get("videoRenderer", {})
                            if not video:
                                continue
                            vid = video.get("videoId", "")
                            title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
                            channel = video.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                            views = video.get("viewCountText", {}).get("simpleText", "")
                            results.append(SearchResult(title=title, url=f"https://www.youtube.com/watch?v={vid}", author=channel, snippet=views))
            return results[:kw.get("count", 20)]
        except Exception:
            return []

    def trending(self, account="default", **kw) -> List[TrendingItem]:
        headers = self._headers(account)
        try:
            resp = httpx.get("https://www.youtube.com/feed/trending", headers=headers, timeout=15)
            items = []
            if resp.status_code == 200:
                import re, json
                match = re.search(r'var ytInitialData = ({.*?});', resp.text)
                if match:
                    data = json.loads(match.group(1))
                    tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
                    for tab in tabs:
                        for section in tab.get("tabRenderer", {}).get("content", {}).get("sectionListRenderer", {}).get("contents", []):
                            for shelf in section.get("itemSectionRenderer", {}).get("contents", []):
                                for item in shelf.get("shelfRenderer", {}).get("content", {}).get("expandedShelfContentsRenderer", {}).get("items", []):
                                    video = item.get("videoRenderer", {})
                                    if video:
                                        vid = video.get("videoId", "")
                                        title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
                                        views = video.get("viewCountText", {}).get("simpleText", "")
                                        items.append(TrendingItem(rank=len(items)+1, title=title, url=f"https://youtube.com/watch?v={vid}", hot_value=views))
            return items[:30]
        except Exception:
            return []

    def me(self, account="default"):
        info = load_account_info(self.name, account)
        if not info: return AccountInfo(platform=self.name, account=account, is_logged_in=False)
        return AccountInfo(platform=self.name, account=account, nickname=info.get("nickname", ""), user_id=info.get("user_id", ""), is_logged_in=True)

    @property
    def cli_group(self):
        @click.group(name="youtube")
        def yt_group():
            """▶️ YouTube — search, publish, trending"""
            pass
        @yt_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, as_json, account):
            """Search YouTube videos."""
            from socialcli.utils.output import print_json, print_table
            results = _platform.search(query, account, count=count)
            if as_json: print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:50], r.author, r.snippet[:20], r.url[:50]] for r in results]
                print_table(f"🔍 {query}", ["Title", "Channel", "Views", "URL"], rows)
        @yt_group.command()
        @click.option("--title", "-t", required=True)
        @click.option("--content", "-c", default="")
        @click.option("--video", "-v", required=True)
        @click.option("--tags", default="")
        @click.option("--account", "-a", default="default")
        def publish(title, content, video, tags, account):
            """Upload video to YouTube."""
            from socialcli.utils import output
            c = Content(title=title, text=content, video=video, tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [])
            result = _platform.publish(c, account)
            if result.success: output.success(f"Uploaded: {result.url}")
            else: output.error(f"Failed: {result.error}")
        return yt_group
