"""
Douyin platform client — wraps dy-cli's API + Playwright engines.

Login: browser QR scan → save cookies
Publish: Playwright upload via creator.douyin.com
Search/Trending: reverse-engineered HTTP API + cookies
"""
from __future__ import annotations

import json
from typing import List

import click
import httpx

from socialcli.platforms.base import (
    Platform, Content, PublishResult, SearchResult, TrendingItem, AccountInfo,
)
from socialcli.auth.cookie_store import load_cookies, cookie_string
from socialcli.auth.browser_login import browser_login

# Douyin API endpoints (reverse-engineered, same as dy-cli)
SEARCH_URL = "https://www.douyin.com/aweme/v1/web/general/search/single/"
TRENDING_URL = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
USER_INFO_URL = "https://creator.douyin.com/web/api/media/user/info/"

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


class DouyinPlatform(Platform):
    name = "douyin"
    display_name = "抖音"
    icon = "🎬"

    LOGIN_URL = "https://creator.douyin.com/"
    SUCCESS_URL = "creator.douyin.com/creator-micro"

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
        # Quick check: verify cookie has sessionid
        has_session = any(c.get("name") == "sessionid" for c in cookies)
        return has_session or len(cookies) > 5

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish video/image to Douyin via Playwright."""
        if not content.video and not content.images:
            return PublishResult(
                success=False, platform=self.name,
                error="Douyin requires video or images",
            )

        # Use Playwright to upload (similar to dy-cli playwright_client)
        try:
            from socialcli.platforms.douyin.browser import douyin_publish
            result = douyin_publish(content, account)
            return result
        except ImportError:
            return PublishResult(
                success=False, platform=self.name,
                error="Playwright not installed. Run: pip install playwright && playwright install chromium",
            )
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search Douyin videos via reverse-engineered API."""
        cookie = cookie_string(self.name, account)
        if not cookie:
            return []

        headers = {
            "User-Agent": DEFAULT_UA,
            "Cookie": cookie,
            "Referer": "https://www.douyin.com/search/" + query,
        }

        params = {
            "keyword": query,
            "search_channel": "aweme_general",
            "sort_type": kwargs.get("sort", "0"),  # 0=综合, 1=最多点赞, 2=最新发布
            "publish_time": kwargs.get("time", "0"),
            "count": kwargs.get("count", "20"),
            "offset": kwargs.get("offset", "0"),
        }

        try:
            resp = httpx.get(SEARCH_URL, params=params, headers=headers, timeout=15)
            data = resp.json()
            results = []

            for item in data.get("data", []):
                aweme = item.get("aweme_info", {})
                if not aweme:
                    continue
                desc = aweme.get("desc", "")
                aweme_id = aweme.get("aweme_id", "")
                author = aweme.get("author", {})
                stats = aweme.get("statistics", {})

                results.append(SearchResult(
                    title=desc[:100],
                    url=f"https://www.douyin.com/video/{aweme_id}",
                    author=author.get("nickname", ""),
                    likes=stats.get("digg_count", 0),
                    comments=stats.get("comment_count", 0),
                    snippet=desc,
                ))

            return results
        except Exception:
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get Douyin hot search list."""
        headers = {"User-Agent": DEFAULT_UA}
        cookie = cookie_string(self.name, account)
        if cookie:
            headers["Cookie"] = cookie

        try:
            resp = httpx.get(TRENDING_URL, headers=headers, timeout=10)
            data = resp.json()
            items = []

            word_list = data.get("data", {}).get("word_list", [])
            for i, item in enumerate(word_list[:50]):
                items.append(TrendingItem(
                    rank=i + 1,
                    title=item.get("word", ""),
                    hot_value=str(item.get("hot_value", "")),
                    url=f"https://www.douyin.com/search/{item.get('word', '')}",
                ))

            return items
        except Exception:
            return []


    # --- CLI subgroup ---
    @property
    def cli_group(self):
        """Click group for `social douyin <command>`."""
        platform = self  # capture for closures

        @click.group(name="douyin")
        def douyin_group():
            """🎬 抖音 — search, publish, trending"""
            pass

        @douyin_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=20, help="Number of results")
        @click.option("--sort", default="0", help="Sort: 0=综合, 1=最多点赞, 2=最新")
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, sort, as_json, account):
            """Search Douyin videos."""
            from socialcli.utils.output import print_json, print_table
            results = platform.search(query, account, count=count, sort=sort)
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:40], r.author, str(r.likes), r.url] for r in results]
                print_table(f"🔍 Search: {query}", ["Title", "Author", "Likes", "URL"], rows)

        @douyin_group.command()
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def trending(count, as_json, account):
            """Get Douyin trending / hot search."""
            from socialcli.utils.output import print_json, print_table
            items = platform.trending(account)[:count]
            if as_json:
                print_json([t.__dict__ for t in items])
            else:
                rows = [[str(t.rank), t.title, t.hot_value] for t in items]
                print_table("🔥 抖音热搜", ["#", "Topic", "Hot Value"], rows)

        @douyin_group.command()
        @click.option("--title", "-t", required=True)
        @click.option("--content", "-c", default="")
        @click.option("--video", "-v", default="")
        @click.option("--image", "-i", multiple=True)
        @click.option("--tags", default="")
        @click.option("--account", "-a", default="default")
        def publish(title, content, video, image, tags, account):
            """Publish to Douyin."""
            from socialcli.utils import output
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
            c = Content(title=title, text=content, video=video, images=list(image), tags=tag_list)
            result = platform.publish(c, account)
            if result.success:
                output.success(f"Published to Douyin: {result.url}")
            else:
                output.error(f"Publish failed: {result.error}")

        return douyin_group
