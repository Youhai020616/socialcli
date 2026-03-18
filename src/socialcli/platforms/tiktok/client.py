"""
TikTok platform client — browser automation + reverse-engineered API.

Login: browser login → capture cookies
Publish: Playwright via tiktok.com/creator
Search/Trending: reverse-engineered API
Reference: douyin client (similar architecture, same parent company)
"""
from __future__ import annotations

import json
from typing import List

import click
import httpx

from socialcli.platforms.base import (
    Platform, Content, PublishResult, SearchResult, TrendingItem, AccountInfo,
)
from socialcli.auth.cookie_store import load_cookies, cookie_string, load_account_info
from socialcli.auth.browser_login import browser_login

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class TiktokPlatform(Platform):
    name = "tiktok"
    display_name = "TikTok"
    icon = "🎵"

    LOGIN_URL = "https://www.tiktok.com/login"
    SUCCESS_URL = "tiktok.com/foryou"

    def login(self, account: str = "default", **kwargs) -> bool:
        return browser_login(
            platform=self.name,
            login_url=self.LOGIN_URL,
            success_url_pattern=self.SUCCESS_URL,
            account=account,
            headless=kwargs.get("headless", False),
        )

    def check_login(self, account: str = "default") -> bool:
        cookies = load_cookies(self.name, account)
        if not cookies:
            return False
        names = {c.get("name") for c in cookies}
        return "sessionid" in names or "sid_tt" in names or len(cookies) > 5

    def _get_headers(self, account: str = "default") -> dict:
        headers = {
            "User-Agent": DEFAULT_UA,
            "Referer": "https://www.tiktok.com/",
        }
        cookie = cookie_string(self.name, account)
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish video to TikTok via Playwright."""
        if not content.video:
            return PublishResult(success=False, platform=self.name, error="TikTok requires a video")

        try:
            from socialcli.platforms.tiktok.browser import tiktok_publish
            return tiktok_publish(content, account)
        except ImportError:
            return PublishResult(success=False, platform=self.name, error="Playwright not installed")
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search TikTok videos."""
        headers = self._get_headers(account)
        count = kwargs.get("count", 20)

        # TikTok search API
        params = {
            "keyword": query,
            "count": count,
            "offset": 0,
            "search_source": "normal_search",
        }

        try:
            resp = httpx.get(
                "https://www.tiktok.com/api/search/general/full/",
                params=params,
                headers=headers,
                timeout=15,
            )

            results = []
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    if item.get("type") != 1:  # video type
                        continue
                    video_info = item.get("item", {})
                    author = video_info.get("author", {})
                    stats = video_info.get("stats", {})

                    results.append(SearchResult(
                        title=video_info.get("desc", "")[:200],
                        url=f"https://www.tiktok.com/@{author.get('uniqueId', '')}/video/{video_info.get('id', '')}",
                        author=f"@{author.get('uniqueId', '')}",
                        likes=stats.get("diggCount", 0),
                        comments=stats.get("commentCount", 0),
                    ))

            return results
        except Exception:
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get TikTok trending."""
        headers = self._get_headers(account)

        try:
            resp = httpx.get(
                "https://www.tiktok.com/api/trending/category/list/",
                headers=headers,
                timeout=10,
            )

            items = []
            if resp.status_code == 200:
                data = resp.json()
                for i, item in enumerate(data.get("data", {}).get("list", [])[:30]):
                    items.append(TrendingItem(
                        rank=i + 1,
                        title=item.get("title", item.get("desc", "")),
                        url=f"https://www.tiktok.com/tag/{item.get('title', '')}",
                        hot_value=str(item.get("stats", {}).get("videoCount", "")),
                    ))

            return items
        except Exception:
            return []

    def me(self, account: str = "default") -> AccountInfo:
        info = load_account_info(self.name, account)
        if not info:
            return AccountInfo(platform=self.name, account=account, is_logged_in=False)
        return AccountInfo(
            platform=self.name, account=account,
            nickname=info.get("nickname", ""), user_id=info.get("user_id", ""),
            is_logged_in=True,
        )

    @property
    def cli_group(self):
        platform = self  # capture for closures

        @click.group(name="tiktok")
        def tiktok_group():
            """🎵 TikTok — search, publish, trending"""
            pass

        @tiktok_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, as_json, account):
            """Search TikTok videos."""
            from socialcli.utils.output import print_json, print_table
            results = platform.search(query, account, count=count)
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:50], r.author, str(r.likes), r.url[:60]] for r in results]
                print_table(f"🔍 Search: {query}", ["Title", "Author", "Likes", "URL"], rows)

        @tiktok_group.command()
        @click.option("--title", "-t", default="")
        @click.option("--content", "-c", default="")
        @click.option("--video", "-v", required=True, help="Video file path")
        @click.option("--tags", default="")
        @click.option("--account", "-a", default="default")
        def publish(title, content, video, tags, account):
            """Publish video to TikTok."""
            from socialcli.utils import output
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
            c = Content(title=title, text=content, video=video, tags=tag_list)
            result = platform.publish(c, account)
            if result.success:
                output.success(f"Published to TikTok: {result.url}")
            else:
                output.error(f"Publish failed: {result.error}")

        return tiktok_group
