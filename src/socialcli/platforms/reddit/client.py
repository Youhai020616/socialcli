"""
Reddit platform client — browser cookie + JSON API.

Login: browser login → capture cookies
Operations: Reddit's public .json API + cookies for auth
Reference: jackwener/rdt-cli (reverse-engineered API + fingerprint)
"""
from __future__ import annotations

import json
import logging
import time
import random
from typing import List

import click
import httpx

logger = logging.getLogger(__name__)

from socialcli.platforms.base import (
    Platform, Content, PublishResult, SearchResult, TrendingItem, AccountInfo,
)
from socialcli.auth.cookie_store import load_cookies
from socialcli.auth.browser_login import browser_login

BASE_URL = "https://www.reddit.com"
OAUTH_URL = "https://oauth.reddit.com"

# Reddit requires a descriptive UA; generic browser UAs get 403 on .json endpoints
DEFAULT_UA = "socialcli/0.1.0 (Python; social media CLI; +https://github.com/socialcli)"


class RedditPlatform(Platform):
    name = "reddit"
    display_name = "Reddit"
    icon = "📖"
    # Reddit requires a descriptive UA; generic browser UAs get 403 on .json endpoints
    default_ua = "socialcli/0.1.0 (Python; social media CLI; +https://github.com/socialcli)"

    LOGIN_URL = "https://www.reddit.com/login/"
    SUCCESS_URL = "reddit.com"

    def login(self, account: str = "default", **kwargs) -> bool:
        """Login to Reddit.

        Strategy: extract cookies from local browser (Chrome/Firefox/Edge)
        first. Falls back to Playwright browser login if extraction fails.
        """
        from socialcli.auth.cookie_store import save_cookies
        from rich.console import Console
        console = Console(stderr=True)

        # Strategy 1: Extract from local browser (fast, gets reddit_session)
        cred = self._extract_browser_cookies()
        if cred:
            cookie_list = [{"name": k, "value": v, "domain": ".reddit.com", "path": "/"} for k, v in cred.items()]
            save_cookies(self.name, cookie_list, account)
            console.print(f"[green]✔ Extracted {len(cookie_list)} cookies from local browser[/green]")
            return True

        # Strategy 2: Playwright (fallback)
        console.print("[dim]Browser cookie extraction failed, opening Playwright login...[/dim]")
        headless = kwargs.get("headless", False)
        return browser_login(
            platform=self.name,
            login_url=self.LOGIN_URL,
            success_url_pattern=self.SUCCESS_URL,
            account=account,
            headless=headless,
        )

    @staticmethod
    def _extract_browser_cookies() -> dict[str, str] | None:
        """Extract Reddit cookies from installed browsers."""
        try:
            import browser_cookie3
        except ImportError:
            logger.debug("browser-cookie3 not installed")
            return None

        for fn in [browser_cookie3.chrome, browser_cookie3.firefox, browser_cookie3.edge, browser_cookie3.brave]:
            try:
                jar = fn(domain_name=".reddit.com")
                cookies = {c.name: c.value for c in jar}
                if "reddit_session" in cookies:
                    logger.debug("Extracted %d cookies via %s", len(cookies), fn.__name__)
                    return cookies
            except Exception:
                continue
        return None

    def check_login(self, account: str = "default") -> bool:
        cookies = load_cookies(self.name, account)
        if not cookies:
            return False
        names = {c.get("name") for c in cookies}
        return "reddit_session" in names

    def _get_headers(self, account: str = "default") -> dict:
        headers = super()._get_headers(account)
        headers["Accept"] = "application/json"
        return headers

    def _modhash(self, account: str = "default") -> str:
        """Get modhash for write operations (CSRF token)."""
        headers = self._get_headers(account)
        try:
            resp = httpx.get(f"{BASE_URL}/api/me.json", headers=headers, timeout=10)
            data = resp.json()
            return data.get("data", {}).get("modhash", "")
        except Exception as exc:
            logger.debug("%s modhash: %s", self.name, exc)
            return ""

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Submit a post to a subreddit via cookie auth + modhash."""
        subreddit = content.extras.get("subreddit", "")
        if not subreddit:
            return PublishResult(
                success=False, platform=self.name,
                error="Reddit requires --subreddit / -r. Example: social reddit publish -t 'Title' -r programming",
            )

        subreddit = subreddit.lstrip("r/").strip("/")

        headers = self._get_headers(account)
        modhash = self._modhash(account)
        if not modhash:
            return PublishResult(
                success=False, platform=self.name,
                error="Cannot get modhash. Cookie may be invalid. Run: social login reddit",
            )

        # Determine post type
        if content.link:
            kind = "link"
        elif content.images:
            kind = "image"
        else:
            kind = "self"

        data = {
            "api_type": "json",
            "kind": kind,
            "sr": subreddit,
            "title": content.title or content.text[:300],
            "uh": modhash,
            "resubmit": "true",
        }

        if kind == "self":
            data["text"] = content.text
        elif kind == "link":
            data["url"] = content.link
        elif kind == "image" and content.images:
            data["url"] = content.images[0]
            data["kind"] = "link"

        time.sleep(random.uniform(1.0, 3.0))

        try:
            resp = httpx.post(
                f"{BASE_URL}/api/submit",
                headers=headers,
                data=data,
                timeout=30,
                follow_redirects=True,
            )
            logger.debug("reddit publish: %d %s", resp.status_code, resp.text[:200])

            result = resp.json()
            json_data = result.get("json", {})
            errors = json_data.get("errors", [])

            if errors:
                error_msg = "; ".join(str(e) for e in errors)
                return PublishResult(success=False, platform=self.name, error=error_msg)

            post_data = json_data.get("data", {})
            post_url = post_data.get("url", "")
            post_id = post_data.get("id", post_data.get("name", ""))

            return PublishResult(
                success=True,
                platform=self.name,
                post_id=post_id,
                url=post_url,
            )
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search Reddit posts."""
        headers = self._get_headers(account)
        subreddit = kwargs.get("subreddit", "")
        sort = kwargs.get("sort", "relevance")  # relevance, hot, top, new
        limit = kwargs.get("count", 25)

        if subreddit:
            url = f"{BASE_URL}/r/{subreddit}/search.json"
            params = {"q": query, "sort": sort, "limit": limit, "restrict_sr": "on"}
        else:
            url = f"{BASE_URL}/search.json"
            params = {"q": query, "sort": sort, "limit": limit}

        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=15)
            data = resp.json()
            results = []

            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                results.append(SearchResult(
                    title=post.get("title", "")[:200],
                    url=f"https://www.reddit.com{post.get('permalink', '')}",
                    author=f"u/{post.get('author', '')}",
                    likes=post.get("ups", 0),
                    comments=post.get("num_comments", 0),
                    snippet=post.get("selftext", "")[:300],
                    created_at=str(post.get("created_utc", "")),
                ))

            return results
        except Exception as exc:
            logger.debug("%s: %s", self.name, exc)
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get Reddit popular posts."""
        headers = self._get_headers(account)

        try:
            resp = httpx.get(f"{BASE_URL}/r/popular.json?limit=25", headers=headers, timeout=15)
            data = resp.json()
            items = []

            children = data.get("data", {}).get("children", [])
            for i, child in enumerate(children):
                post = child.get("data", {})
                items.append(TrendingItem(
                    rank=i + 1,
                    title=post.get("title", "")[:100],
                    url=f"https://www.reddit.com{post.get('permalink', '')}",
                    hot_value=f"{post.get('ups', 0)} upvotes",
                    category=f"r/{post.get('subreddit', '')}",
                ))

            return items
        except Exception as exc:
            logger.debug("%s: %s", self.name, exc)
            return []

    def like(self, target_id: str, account: str = "default", **kwargs) -> bool:
        """Upvote a post."""
        headers = self._get_headers(account)
        modhash = self._modhash(account)
        try:
            resp = httpx.post(
                f"{BASE_URL}/api/vote",
                headers=headers,
                data={"id": target_id, "dir": "1", "uh": modhash},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as exc:
            logger.debug("%s: %s", self.name, exc)
            return False

    def comment(self, target_id: str, text: str, account: str = "default", **kwargs) -> bool:
        """Comment on a post."""
        headers = self._get_headers(account)
        modhash = self._modhash(account)
        try:
            resp = httpx.post(
                f"{BASE_URL}/api/comment",
                headers=headers,
                data={"thing_id": target_id, "text": text, "uh": modhash, "api_type": "json"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as exc:
            logger.debug("%s: %s", self.name, exc)
            return False

    # --- CLI subgroup ---
    @property
    def cli_group(self):
        platform = self  # capture for closures

        @click.group(name="reddit")
        def reddit_group():
            """📖 Reddit — search, publish, trending, interact"""
            pass

        @reddit_group.command()
        @click.argument("query")
        @click.option("--subreddit", "-r", default="", help="Search within subreddit")
        @click.option("--sort", default="relevance", help="relevance/hot/top/new")
        @click.option("--count", "-n", default=25)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, subreddit, sort, count, as_json, account):
            """Search Reddit posts."""
            from socialcli.utils.output import print_json, print_table
            results = platform.search(query, account, subreddit=subreddit, sort=sort, count=count)
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:50], r.author, str(r.likes), f"💬{r.comments}", r.url[:60]] for r in results]
                print_table(f"🔍 Search: {query}", ["Title", "Author", "↑", "Comments", "URL"], rows)

        @reddit_group.command()
        @click.option("--count", "-n", default=25)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def trending(count, as_json, account):
            """Get Reddit popular posts."""
            from socialcli.utils.output import print_json, print_table
            items = platform.trending(account)[:count]
            if as_json:
                print_json([t.__dict__ for t in items])
            else:
                rows = [[str(t.rank), t.title[:50], t.category, t.hot_value] for t in items]
                print_table("🔥 Reddit Popular", ["#", "Title", "Subreddit", "Upvotes"], rows)

        @reddit_group.command()
        @click.option("--title", "-t", required=True, help="Post title")
        @click.option("--content", "-c", default="", help="Post body (Markdown)")
        @click.option("--subreddit", "-r", required=True, help="Target subreddit")
        @click.option("--link", "-l", default="", help="Link URL (for link posts)")
        @click.option("--account", "-a", default="default")
        def publish(title, content, subreddit, link, account):
            """Submit a post to a subreddit."""
            from socialcli.utils import output
            c = Content(title=title, text=content, link=link, extras={"subreddit": subreddit})
            result = platform.publish(c, account)
            if result.success:
                output.success(f"Posted to r/{subreddit}: {result.url}")
            else:
                output.error(f"Post failed: {result.error}")

        @reddit_group.command()
        @click.argument("post_id")
        @click.option("--account", "-a", default="default")
        def upvote(post_id, account):
            """Upvote a post."""
            from socialcli.utils import output
            if platform.like(post_id, account):
                output.success("Upvoted")
            else:
                output.error("Upvote failed")

        return reddit_group
