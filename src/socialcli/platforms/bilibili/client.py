"""
Bilibili (B站) platform client — reverse-engineered API.

Login: browser QR scan → capture cookies
Operations: Bilibili Web API + cookies
Reference: jackwener/bilibili-cli
"""
from __future__ import annotations

from typing import List

import click
import httpx

from socialcli.platforms.base import (
    Platform, Content, PublishResult, SearchResult, TrendingItem, AccountInfo,
)
from socialcli.auth.cookie_store import load_cookies, cookie_string, load_account_info
from socialcli.auth.browser_login import browser_login

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)

# Bilibili API endpoints
SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/all/v2"
HOT_URL = "https://api.bilibili.com/x/web-interface/ranking/v2"
TRENDING_URL = "https://api.bilibili.com/x/web-interface/search/square"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"


class BilibiliPlatform(Platform):
    name = "bilibili"
    display_name = "B站"
    icon = "📺"

    LOGIN_URL = "https://passport.bilibili.com/login"
    SUCCESS_URL = "bilibili.com"

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
        return "SESSDATA" in names or "bili_jct" in names or len(cookies) > 5

    def _get_headers(self, account: str = "default") -> dict:
        headers = {
            "User-Agent": DEFAULT_UA,
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
        }
        cookie = cookie_string(self.name, account)
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish video to Bilibili via Playwright."""
        if not content.video:
            return PublishResult(success=False, platform=self.name, error="Bilibili requires a video")

        try:
            from socialcli.platforms.bilibili.browser import bilibili_publish
            return bilibili_publish(content, account)
        except ImportError:
            return PublishResult(success=False, platform=self.name, error="Playwright not installed")
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search Bilibili videos."""
        headers = self._get_headers(account)
        count = kwargs.get("count", 20)

        params = {
            "keyword": query,
            "page": 1,
            "page_size": count,
            "search_type": "video",
        }

        try:
            resp = httpx.get(
                "https://api.bilibili.com/x/web-interface/search/type",
                params=params,
                headers=headers,
                timeout=15,
            )

            results = []
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", {}).get("result", []):
                    # Strip HTML tags from title
                    title = item.get("title", "")
                    import re
                    title = re.sub(r"<[^>]+>", "", title)

                    results.append(SearchResult(
                        title=title[:200],
                        url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                        author=item.get("author", ""),
                        likes=item.get("like", 0),
                        comments=item.get("review", 0),
                        snippet=item.get("description", "")[:300],
                    ))

            return results
        except Exception:
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get Bilibili popular videos (热门)."""
        headers = self._get_headers(account)
        count = kwargs.get("count", 30)

        try:
            # Use /popular endpoint (no wbi auth needed) instead of /ranking/v2
            resp = httpx.get(
                "https://api.bilibili.com/x/web-interface/popular",
                params={"ps": min(count, 50), "pn": 1},
                headers=headers,
                timeout=10,
            )

            items = []
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") != 0:
                    return items
                for i, item in enumerate(data.get("data", {}).get("list", [])[:count]):
                    stat = item.get("stat", {})
                    items.append(TrendingItem(
                        rank=i + 1,
                        title=item.get("title", ""),
                        url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                        hot_value=f"{stat.get('view', 0)} views",
                        category=item.get("tname", ""),
                    ))

            return items
        except Exception:
            return []

    def me(self, account: str = "default") -> AccountInfo:
        """Get logged-in user info from nav API."""
        headers = self._get_headers(account)
        try:
            resp = httpx.get(NAV_URL, headers=headers, timeout=10)
            data = resp.json().get("data", {})
            if data.get("isLogin"):
                return AccountInfo(
                    platform=self.name, account=account,
                    nickname=data.get("uname", ""),
                    user_id=str(data.get("mid", "")),
                    is_logged_in=True,
                )
        except Exception:
            pass

        info = load_account_info(self.name, account)
        if info:
            return AccountInfo(
                platform=self.name, account=account,
                nickname=info.get("nickname", ""), user_id=info.get("user_id", ""),
                is_logged_in=True,
            )
        return AccountInfo(platform=self.name, account=account, is_logged_in=False)

    @property
    def cli_group(self):
        platform = self  # capture for closures

        @click.group(name="bilibili")
        def bili_group():
            """📺 B站 — search, publish, trending"""
            pass

        @bili_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, as_json, account):
            """Search Bilibili videos."""
            from socialcli.utils.output import print_json, print_table
            results = platform.search(query, account, count=count)
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:40], r.author, str(r.likes), r.url[:50]] for r in results]
                print_table(f"🔍 Search: {query}", ["Title", "UP主", "Likes", "URL"], rows)

        @bili_group.command()
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def trending(count, as_json, account):
            """Get Bilibili hot ranking."""
            from socialcli.utils.output import print_json, print_table
            items = platform.trending(account)[:count]
            if as_json:
                print_json([t.__dict__ for t in items])
            else:
                rows = [[str(t.rank), t.title[:40], t.category, t.hot_value] for t in items]
                print_table("🔥 B站热门", ["#", "Title", "Category", "Views"], rows)

        @bili_group.command()
        @click.option("--title", "-t", required=True)
        @click.option("--content", "-c", default="")
        @click.option("--video", "-v", required=True)
        @click.option("--tags", default="")
        @click.option("--account", "-a", default="default")
        def publish(title, content, video, tags, account):
            """Publish video to Bilibili."""
            from socialcli.utils import output
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
            c = Content(title=title, text=content, video=video, tags=tag_list)
            result = platform.publish(c, account)
            if result.success:
                output.success(f"Published to B站: {result.url}")
            else:
                output.error(f"Publish failed: {result.error}")

        return bili_group
