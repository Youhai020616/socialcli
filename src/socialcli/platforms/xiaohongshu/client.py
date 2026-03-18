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
from socialcli.auth.cookie_store import load_cookies, cookie_string
from socialcli.auth.browser_login import browser_login

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)


def _xhs_search_id() -> str:
    """Generate XHS search_id (base36 of timestamp<<64 + random)."""
    import time, random
    e = int(time.time() * 1000) << 64
    t = random.randint(0, 2147483646)
    num = e + t
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""
    while num > 0:
        result = alphabet[num % 36] + result
        num //= 36
    return result


class XiaohongshuPlatform(Platform):
    name = "xhs"
    display_name = "小红书"
    icon = "📕"
    cookie_domain = ".xiaohongshu.com"
    required_cookies = ["a1", "web_session"]

    LOGIN_URL = "https://creator.xiaohongshu.com/"
    SUCCESS_URL = "creator.xiaohongshu.com/home"

    def login(self, account: str = "default", **kwargs) -> bool:
        from rich.console import Console
        console = Console(stderr=True)

        if self.login_with_browser_cookies(account):
            cookies = load_cookies(self.name, account) or []
            console.print(f"[green]✔ Extracted {len(cookies)} 小红书 cookies from local browser[/green]")
            return True

        console.print("[dim]Browser cookie extraction failed, opening Playwright login...[/dim]")
        return browser_login(
            platform=self.name, login_url=self.LOGIN_URL,
            success_url_pattern=self.SUCCESS_URL,
            account=account, headless=kwargs.get("headless", False),
        )

    def check_login(self, account: str = "default") -> bool:
        cookies = load_cookies(self.name, account)
        if not cookies:
            return False
        names = {c.get("name") for c in cookies}
        return "a1" in names and "web_session" in names

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
        """Search Xiaohongshu notes with xhshow API signing."""
        import json as _json
        import logging
        import urllib.parse
        logger = logging.getLogger(__name__)

        cookies_raw = load_cookies(self.name, account) or []
        if not cookies_raw:
            return []
        cookies_dict = {c["name"]: c["value"] for c in cookies_raw if "name" in c}
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies_dict.items())

        uri = "/api/sns/web/v1/search/notes"
        search_url = f"https://edith.xiaohongshu.com{uri}"
        payload = {
            "keyword": query,
            "page": kwargs.get("page", 1),
            "page_size": min(kwargs.get("count", 20), 20),
            "search_id": _xhs_search_id(),
            "sort": kwargs.get("sort", "general"),
            "note_type": 0,
            "ext_flags": [],
            "filters": [],
            "geo": "",
            "image_formats": ["jpg", "webp", "avif"],
        }

        # Full browser-like headers (matching xiaohongshu-cli reference)
        headers = {
            "user-agent": DEFAULT_UA,
            "content-type": "application/json;charset=UTF-8",
            "cookie": cookie_str,
            "origin": "https://www.xiaohongshu.com",
            "referer": f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(query)}&source=web_search_result_notes",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "dnt": "1",
            "priority": "u=1, i",
        }

        # Add xhshow signing headers
        try:
            from xhshow import CryptoConfig, SessionManager, Xhshow
            config = CryptoConfig().with_overrides(
                PUBLIC_USERAGENT=DEFAULT_UA,
                SIGNATURE_DATA_TEMPLATE={"x0": "4.2.6", "x1": "xhs-pc-web", "x2": "macOS", "x3": "", "x4": ""},
                SIGNATURE_XSCOMMON_TEMPLATE={"s0": 5, "s1": "", "x0": "1", "x1": "4.2.6", "x2": "macOS", "x3": "xhs-pc-web", "x4": "4.86.0", "x5": "", "x6": "", "x7": "", "x8": "", "x9": -596800761, "x10": 0, "x11": "normal"},
            )
            xhshow = Xhshow(config)
            session = SessionManager(config)
            sign_headers = xhshow.sign_headers_post(uri, cookies_dict, payload=payload, session=session)
            headers.update(sign_headers)
            logger.debug("xhs search: signed with xhshow")
        except ImportError:
            logger.debug("xhs search: xhshow not available, request may fail")

        try:
            body = _json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
            resp = httpx.post(search_url, content=body, headers=headers, timeout=15)
            logger.debug("xhs search: %d, len=%d", resp.status_code, len(resp.content))
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


    # --- CLI subgroup ---
    @property
    def cli_group(self):
        platform = self  # capture for closures

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
            results = platform.search(query, account, count=count, sort=sort)
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
            result = platform.publish(c, account)
            if result.success:
                output.success(f"Published to 小红书: {result.url}")
            else:
                output.error(f"Publish failed: {result.error}")

        return xhs_group
