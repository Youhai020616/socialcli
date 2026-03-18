"""
Weibo (微博) platform client — reverse-engineered Ajax API.

Reference: jackwener/weibo-cli
Login: browser QR scan → capture cookies
Operations: weibo.com Ajax API + cookies
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

# Weibo Ajax API endpoints
HOT_SEARCH_URL = "https://weibo.com/ajax/side/hotSearch"
HOT_BAND_URL = "https://weibo.com/ajax/statuses/hot_band"
SEARCH_URL = "https://weibo.com/ajax/side/search"
FRIENDS_TIMELINE_URL = "https://weibo.com/ajax/feed/friendstimeline"
PROFILE_INFO_URL = "https://weibo.com/ajax/profile/info"
MOBILE_SEARCH_URL = "https://m.weibo.cn/api/container/getIndex"


class WeiboPlatform(Platform):
    name = "weibo"
    display_name = "微博"
    icon = "🔥"

    LOGIN_URL = "https://weibo.com/login.php"
    SUCCESS_URL = "weibo.com"

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
        return "SUBP" in names or "SUB" in names or len(cookies) > 5

    def _get_headers(self, account: str = "default") -> dict:
        headers = {
            "User-Agent": DEFAULT_UA,
            "Referer": "https://weibo.com/",
            "X-Requested-With": "XMLHttpRequest",
        }
        cookie = cookie_string(self.name, account)
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish a weibo via Playwright."""
        try:
            from socialcli.platforms.weibo.browser import weibo_publish
            return weibo_publish(content, account)
        except ImportError:
            return PublishResult(success=False, platform=self.name, error="Playwright not installed")
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search Weibo via mobile API."""
        headers = self._get_headers(account)
        headers["Referer"] = "https://m.weibo.cn/"

        params = {
            "containerid": f"100103type=1&q={query}",
            "page_type": "searchall",
            "page": kwargs.get("page", 1),
        }

        try:
            resp = httpx.get(MOBILE_SEARCH_URL, params=params, headers=headers, timeout=15)
            results = []

            if resp.status_code == 200:
                data = resp.json()
                cards = data.get("data", {}).get("cards", [])
                for card in cards:
                    for item in card.get("card_group", []):
                        mblog = item.get("mblog", {})
                        if not mblog:
                            continue
                        user = mblog.get("user", {})
                        text = mblog.get("text", "")
                        # Strip HTML
                        import re
                        text = re.sub(r"<[^>]+>", "", text)

                        results.append(SearchResult(
                            title=text[:200],
                            url=f"https://weibo.com/{user.get('id', '')}/{mblog.get('bid', '')}",
                            author=user.get("screen_name", ""),
                            likes=mblog.get("attitudes_count", 0),
                            comments=mblog.get("comments_count", 0),
                            snippet=text[:300],
                        ))

            return results
        except Exception:
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get Weibo hot search."""
        headers = {"User-Agent": DEFAULT_UA}

        try:
            resp = httpx.get(HOT_SEARCH_URL, headers=headers, timeout=10)
            items = []

            if resp.status_code == 200:
                data = resp.json()
                realtime = data.get("data", {}).get("realtime", [])
                for i, item in enumerate(realtime[:50]):
                    items.append(TrendingItem(
                        rank=i + 1,
                        title=item.get("word", item.get("note", "")),
                        url=f"https://s.weibo.com/weibo?q=%23{item.get('word', '')}%23",
                        hot_value=str(item.get("num", item.get("raw_hot", ""))),
                        category=item.get("category", ""),
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

        @click.group(name="weibo")
        def weibo_group():
            """🔥 微博 — search, publish, trending"""
            pass

        @weibo_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, as_json, account):
            """Search Weibo posts."""
            from socialcli.utils.output import print_json, print_table
            results = platform.search(query, account)[:count]
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:40], r.author, str(r.likes), r.url[:50]] for r in results]
                print_table(f"🔍 Search: {query}", ["Content", "Author", "Likes", "URL"], rows)

        @weibo_group.command()
        @click.option("--count", "-n", default=30)
        @click.option("--json", "as_json", is_flag=True)
        def trending(count, as_json):
            """Get Weibo hot search (微博热搜)."""
            from socialcli.utils.output import print_json, print_table
            items = platform.trending()[:count]
            if as_json:
                print_json([t.__dict__ for t in items])
            else:
                rows = [[str(t.rank), t.title, t.hot_value] for t in items]
                print_table("🔥 微博热搜", ["#", "Topic", "Hot"], rows)

        @weibo_group.command()
        @click.argument("text")
        @click.option("--image", "-i", multiple=True)
        @click.option("--account", "-a", default="default")
        def publish(text, image, account):
            """Publish a weibo."""
            from socialcli.utils import output
            c = Content(text=text, images=list(image))
            result = platform.publish(c, account)
            if result.success:
                output.success(f"Weibo posted: {result.url}")
            else:
                output.error(f"Post failed: {result.error}")

        return weibo_group
