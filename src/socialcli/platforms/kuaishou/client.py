"""
Kuaishou (快手) platform client — browser automation.

Reference: AiToEarn/aitoearn-electron/electron/plat/Kwai
Login: browser QR scan
Publish: Playwright via cp.kuaishou.com
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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class KuaishouPlatform(Platform):
    name = "kuaishou"
    display_name = "快手"
    icon = "⚡"

    LOGIN_URL = "https://cp.kuaishou.com/"
    SUCCESS_URL = "cp.kuaishou.com/article"

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
        return len(cookies) > 3

    def _get_headers(self, account: str = "default") -> dict:
        cookie = cookie_string(self.name, account)
        return {
            "User-Agent": DEFAULT_UA,
            "Cookie": cookie,
            "Referer": "https://cp.kuaishou.com/",
        }

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        if not content.video:
            return PublishResult(success=False, platform=self.name, error="Kuaishou requires a video")
        try:
            from socialcli.platforms.kuaishou.browser import kuaishou_publish
            return kuaishou_publish(content, account)
        except ImportError:
            return PublishResult(success=False, platform=self.name, error="Playwright not installed")
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search Kuaishou via web API."""
        headers = self._get_headers(account)
        try:
            resp = httpx.post(
                "https://www.kuaishou.com/graphql",
                headers=headers,
                json={
                    "operationName": "visionSearchPhoto",
                    "variables": {"keyword": query, "page": "search_result", "pcursor": ""},
                    "query": "query visionSearchPhoto($keyword: String, $pcursor: String, $page: String) { visionSearchPhoto(keyword: $keyword, pcursor: $pcursor, page: $page) { feeds { photo { id caption likeCount viewCount timestamp webUrl user { name id } } } } }",
                },
                timeout=15,
            )
            results = []
            if resp.status_code == 200:
                feeds = resp.json().get("data", {}).get("visionSearchPhoto", {}).get("feeds", [])
                for item in feeds[:kwargs.get("count", 20)]:
                    photo = item.get("photo", {})
                    user = photo.get("user", {})
                    results.append(SearchResult(
                        title=photo.get("caption", "")[:200],
                        url=photo.get("webUrl", f"https://www.kuaishou.com/short-video/{photo.get('id', '')}"),
                        author=user.get("name", ""),
                        likes=photo.get("likeCount", 0),
                    ))
            return results
        except Exception:
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        return []  # Kuaishou doesn't have a simple public trending API

    def me(self, account: str = "default") -> AccountInfo:
        info = load_account_info(self.name, account)
        if not info:
            return AccountInfo(platform=self.name, account=account, is_logged_in=False)
        return AccountInfo(platform=self.name, account=account,
                           nickname=info.get("nickname", ""), user_id=info.get("user_id", ""),
                           is_logged_in=True)

    @property
    def cli_group(self):
        @click.group(name="kuaishou")
        def ks_group():
            """⚡ 快手 — search, publish"""
            pass

        @ks_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, as_json, account):
            """Search Kuaishou videos."""
            from socialcli.utils.output import print_json, print_table
            results = _platform.search(query, account, count=count)
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:40], r.author, str(r.likes), r.url[:50]] for r in results]
                print_table(f"🔍 Search: {query}", ["Title", "Author", "Likes", "URL"], rows)

        @ks_group.command()
        @click.option("--title", "-t", default="")
        @click.option("--content", "-c", default="")
        @click.option("--video", "-v", required=True)
        @click.option("--account", "-a", default="default")
        def publish(title, content, video, account):
            """Publish video to Kuaishou."""
            from socialcli.utils import output
            c = Content(title=title, text=content, video=video)
            result = _platform.publish(c, account)
            if result.success:
                output.success(f"Published: {result.url}")
            else:
                output.error(f"Failed: {result.error}")

        return ks_group
