"""
LinkedIn platform client — browser automation + reverse-engineered API.

Login: browser login → capture cookies
Publish: Playwright via linkedin.com
Search: reverse-engineered Voyager API
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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class LinkedinPlatform(Platform):
    name = "linkedin"
    display_name = "LinkedIn"
    icon = "💼"

    LOGIN_URL = "https://www.linkedin.com/login"
    SUCCESS_URL = "linkedin.com/feed"

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
        return "li_at" in names or "JSESSIONID" in names or len(cookies) > 5

    def _get_headers(self, account: str = "default") -> dict:
        cookies = load_cookies(self.name, account) or []
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if "name" in c)
        csrf = next((c["value"] for c in cookies if c.get("name") == "JSESSIONID"), "")
        csrf = csrf.strip('"')

        headers = {
            "User-Agent": DEFAULT_UA,
            "X-Restli-Protocol-Version": "2.0.0",
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
        }
        if cookie_str:
            headers["Cookie"] = cookie_str
        if csrf:
            headers["Csrf-Token"] = csrf
        return headers

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish a post to LinkedIn via Playwright."""
        try:
            from socialcli.platforms.linkedin.browser import linkedin_publish
            return linkedin_publish(content, account)
        except ImportError:
            return PublishResult(success=False, platform=self.name, error="Playwright not installed")
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search LinkedIn posts via Voyager API."""
        headers = self._get_headers(account)
        count = kwargs.get("count", 10)

        params = {
            "keywords": query,
            "origin": "GLOBAL_SEARCH_HEADER",
            "q": "all",
            "count": count,
            "filters": "List(resultType->CONTENT)",
        }

        try:
            resp = httpx.get(
                "https://www.linkedin.com/voyager/api/graphql",
                params=params,
                headers=headers,
                timeout=15,
            )

            results = []
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("data", {}).get("data", {}).get("searchDashClustersByAll", {}).get("elements", [])
                for cluster in elements:
                    for item in cluster.get("items", []):
                        entity = item.get("item", {}).get("entityResult", {})
                        if not entity:
                            continue
                        title_text = entity.get("title", {}).get("text", "")
                        summary = entity.get("summary", {}).get("text", "")
                        nav_url = entity.get("navigationUrl", "")

                        if title_text:
                            results.append(SearchResult(
                                title=title_text[:200],
                                url=nav_url,
                                snippet=summary[:300],
                            ))

            return results[:count]
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

        @click.group(name="linkedin")
        def linkedin_group():
            """💼 LinkedIn — search, publish"""
            pass

        @linkedin_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=10)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, as_json, account):
            """Search LinkedIn posts."""
            from socialcli.utils.output import print_json, print_table
            results = platform.search(query, account, count=count)
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:50], r.snippet[:40], r.url[:60]] for r in results]
                print_table(f"🔍 Search: {query}", ["Title", "Snippet", "URL"], rows)

        @linkedin_group.command()
        @click.argument("text")
        @click.option("--image", "-i", multiple=True)
        @click.option("--account", "-a", default="default")
        def publish(text, image, account):
            """Publish a LinkedIn post."""
            from socialcli.utils import output
            c = Content(text=text, images=list(image))
            result = platform.publish(c, account)
            if result.success:
                output.success(f"Posted to LinkedIn: {result.url}")
            else:
                output.error(f"Post failed: {result.error}")

        return linkedin_group
