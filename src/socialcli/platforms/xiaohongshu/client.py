"""
Xiaohongshu platform client — browser automation via CDP/Playwright.

Login: browser QR scan → save cookies
Publish: CDP automation via creator.xiaohongshu.com
Search: reverse-engineered HTTP API
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

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


class XiaohongshuPlatform(Platform):
    name = "xhs"
    display_name = "小红书"
    icon = "📕"

    LOGIN_URL = "https://creator.xiaohongshu.com/"
    SUCCESS_URL = "creator.xiaohongshu.com/home"

    def login(self, account: str = "default", **kwargs) -> bool:
        headless = kwargs.get("headless", False)
        return browser_login(
            platform=self.name,
            login_url=self.LOGIN_URL,
            success_url_pattern=self.SUCCESS_URL,
            account=account,
            headless=headless,
        )

    def check_login(self, account: str = "default") -> bool:
        cookies = load_cookies(self.name, account)
        if not cookies:
            return False
        return len(cookies) > 3

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish to Xiaohongshu via browser automation."""
        if not content.images and not content.video:
            return PublishResult(
                success=False, platform=self.name,
                error="Xiaohongshu requires images or video",
            )

        try:
            from socialcli.platforms.xiaohongshu.browser import xhs_publish
            return xhs_publish(content, account)
        except ImportError:
            return PublishResult(
                success=False, platform=self.name,
                error="Playwright not installed",
            )
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search Xiaohongshu notes."""
        cookie = cookie_string(self.name, account)
        if not cookie:
            return []

        headers = {
            "User-Agent": DEFAULT_UA,
            "Cookie": cookie,
            "Referer": "https://www.xiaohongshu.com/",
            "Origin": "https://www.xiaohongshu.com",
        }

        search_url = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
        payload = {
            "keyword": query,
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("count", 20),
            "sort": kwargs.get("sort", "general"),  # general / time_descending / popularity_descending
        }

        try:
            resp = httpx.post(search_url, json=payload, headers=headers, timeout=15)
            data = resp.json()
            results = []

            for item in data.get("data", {}).get("items", []):
                note = item.get("note_card", {})
                user = note.get("user", {})
                interact = note.get("interact_info", {})

                results.append(SearchResult(
                    title=note.get("display_title", "")[:100],
                    url=f"https://www.xiaohongshu.com/explore/{item.get('id', '')}",
                    author=user.get("nickname", ""),
                    likes=int(interact.get("liked_count", "0")),
                    snippet=note.get("desc", ""),
                    thumbnail=note.get("cover", {}).get("url_default", ""),
                ))

            return results
        except Exception:
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get Xiaohongshu trending topics."""
        # XHS doesn't have a public trending API — use search suggestions
        return []

    def me(self, account: str = "default") -> AccountInfo:
        info = load_account_info(self.name, account)
        if not info:
            return AccountInfo(platform=self.name, account=account, is_logged_in=False)
        return AccountInfo(
            platform=self.name,
            account=account,
            nickname=info.get("nickname", ""),
            user_id=info.get("user_id", ""),
            is_logged_in=True,
        )

    # --- CLI subgroup ---
    @property
    def cli_group(self):
        @click.group(name="xhs")
        def xhs_group():
            """📕 小红书 — search, publish"""
            pass

        @xhs_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=20)
        @click.option("--sort", default="general", help="general/time_descending/popularity_descending")
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, sort, as_json, account):
            """Search Xiaohongshu notes."""
            from socialcli.utils.output import print_json, print_table
            results = _platform.search(query, account, count=count, sort=sort)
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:40], r.author, str(r.likes), r.url] for r in results]
                print_table(f"🔍 Search: {query}", ["Title", "Author", "Likes", "URL"], rows)

        @xhs_group.command()
        @click.option("--title", "-t", required=True)
        @click.option("--content", "-c", default="")
        @click.option("--image", "-i", multiple=True)
        @click.option("--video", "-v", default="")
        @click.option("--tags", default="")
        @click.option("--account", "-a", default="default")
        def publish(title, content, image, video, tags, account):
            """Publish to Xiaohongshu."""
            from socialcli.utils import output
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
            c = Content(title=title, text=content, images=list(image), video=video, tags=tag_list)
            result = _platform.publish(c, account)
            if result.success:
                output.success(f"Published to 小红书: {result.url}")
            else:
                output.error(f"Publish failed: {result.error}")

        return xhs_group
