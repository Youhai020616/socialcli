"""
Douyin platform client — Playwright-based for search/trending (no signature needed).

Login: browser QR scan → save cookies
Publish: Playwright upload via creator.douyin.com
Search/Trending: Playwright browser scraping (bypasses anti-crawl)
"""
from __future__ import annotations

import json
import logging
import re
from typing import List

import click

from socialcli.platforms.base import (
    Platform, Content, PublishResult, SearchResult, TrendingItem,
)
from socialcli.auth.cookie_store import load_cookies, cookie_string
from socialcli.auth.browser_login import browser_login

logger = logging.getLogger(__name__)


# ── Playwright helpers ────────────────────────────────────────────────


async def _douyin_trending() -> List[TrendingItem]:
    """Scrape Douyin trending from douyin.com/hot via Playwright."""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://www.douyin.com/hot", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)

            items_raw = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/hot/"]');
                links.forEach(a => {
                    const title = a.textContent.trim().replace(/^\\d+/, '').trim();
                    const href = a.getAttribute('href') || '';
                    if (title && title.length > 2 && !title.includes('抖音热点')) {
                        results.push({
                            title: title,
                            url: 'https://www.douyin.com' + href,
                        });
                    }
                });
                return results;
            }
            """)

            items = []
            for i, raw in enumerate(items_raw[:50]):
                items.append(TrendingItem(
                    rank=i + 1,
                    title=raw["title"],
                    url=raw["url"],
                ))
            logger.debug("douyin trending: %d items", len(items))
            return items
        finally:
            await browser.close()


async def _douyin_search(query: str, count: int = 20) -> List[SearchResult]:
    """Search Douyin via Playwright browser scraping."""
    from playwright.async_api import async_playwright
    import urllib.parse

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            url = f"https://www.douyin.com/search/{urllib.parse.quote(query)}?type=video"
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(5000)

            items_raw = await page.evaluate("""
            () => {
                const results = [];
                // Video cards in search results
                const cards = document.querySelectorAll('[class*="search-result"] a[href*="/video/"], [class*="VideoCard"] a, a[href*="/video/"]');
                const seen = new Set();
                cards.forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const match = href.match(/\\/video\\/(\\d+)/);
                    if (!match || seen.has(match[1])) return;
                    seen.add(match[1]);
                    
                    const title = a.textContent.trim().substring(0, 200);
                    if (!title || title.length < 3) return;
                    
                    results.push({
                        title: title,
                        url: href.startsWith('http') ? href : 'https://www.douyin.com' + href,
                        video_id: match[1],
                    });
                });
                return results;
            }
            """)

            results = []
            for raw in items_raw[:count]:
                results.append(SearchResult(
                    title=raw["title"][:100],
                    url=raw["url"],
                ))
            logger.debug("douyin search '%s': %d results", query, len(results))
            return results
        finally:
            await browser.close()

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
        """Search Douyin videos via Playwright (reliable, no signature needed)."""
        import asyncio
        count = kwargs.get("count", 20)
        try:
            return asyncio.run(_douyin_search(query, count))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("douyin search: %s", exc)
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get Douyin trending via Playwright (reliable, no signature needed)."""
        import asyncio
        try:
            return asyncio.run(_douyin_trending())
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("douyin trending: %s", exc)
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
