"""
Twitter/X platform client — reverse-engineered GraphQL API.

queryId resolution: fallback constants → GitHub community source → JS bundle scan.
Reference: github/twitter-cli (jackwener/twitter-cli)
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
from typing import List

import click
import httpx

from socialcli.platforms.base import (
    Platform, Content, PublishResult, SearchResult, TrendingItem,
)
from socialcli.auth.cookie_store import load_cookies
from socialcli.auth.browser_login import browser_login

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
GRAPHQL_URL = "https://x.com/i/api/graphql"
TRENDING_URL = "https://x.com/i/api/2/guide.json"

# Community-maintained queryId source (fa0311/twitter-openapi)
_OPENAPI_URL = (
    "https://raw.githubusercontent.com/fa0311/"
    "twitter-openapi/refs/heads/main/src/config/placeholder.json"
)

# Fallback queryIds — last known working values
_FALLBACK_IDS = {
    "SearchTimeline": "MJpyQGqgklrVl_0X9gNy3A",
    "CreateTweet": "bDE2rBtZb3uyrczSZ_pI9g",
}

# Default feature flags for GraphQL requests
_FEATURES = {
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "view_counts_everywhere_api_enabled": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_media_download_video_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "responsive_web_enhance_cards_enabled": False,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
}

# ── queryId resolution ───────────────────────────────────────────────────

_cached_ids: dict[str, str] = {}
_bundles_scanned = False


def _scan_js_bundles() -> None:
    """Scan x.com JS bundles for live queryIds using curl_cffi."""
    global _bundles_scanned
    if _bundles_scanned:
        return
    _bundles_scanned = True

    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        logger.debug("curl_cffi not available for JS bundle scan")
        return

    try:
        resp = cffi_requests.get("https://x.com", impersonate="chrome", timeout=15)
        script_pattern = re.compile(
            r'(?:src|href)="(https://abs\.twimg\.com/responsive-web/client-web[^"]+\.js)"'
        )
        scripts = script_pattern.findall(resp.text)
        logger.debug("Found %d JS bundles on x.com", len(scripts))

        op_pattern = re.compile(
            r'queryId:\s*"([A-Za-z0-9_-]+)"[^}]{0,200}operationName:\s*"([^"]+)"'
        )
        for script_url in scripts[:15]:
            try:
                bundle = cffi_requests.get(script_url, impersonate="chrome", timeout=10).text
                for match in op_pattern.finditer(bundle):
                    qid, op = match.group(1), match.group(2)
                    _cached_ids.setdefault(op, qid)
            except Exception:
                continue
        logger.debug("JS bundle scan: cached %d queryIds", len(_cached_ids))
    except Exception as exc:
        logger.debug("JS bundle scan failed: %s", exc)


def _resolve_query_id(operation: str) -> str:
    """Resolve queryId: cache → JS bundles → GitHub → fallback."""
    if operation in _cached_ids:
        return _cached_ids[operation]

    # Try JS bundle scan (most reliable, gets live IDs)
    _scan_js_bundles()
    if operation in _cached_ids:
        return _cached_ids[operation]

    # Try GitHub community source
    try:
        resp = httpx.get(_OPENAPI_URL, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            qid = data.get(operation, {}).get("queryId")
            if qid:
                _cached_ids[operation] = qid
                logger.debug("queryId %s=%s (from GitHub)", operation, qid)
                return qid
    except Exception as exc:
        logger.debug("GitHub queryId fetch failed: %s", exc)

    # Fallback
    fallback = _FALLBACK_IDS.get(operation, "")
    if fallback:
        _cached_ids[operation] = fallback
        logger.debug("queryId %s=%s (fallback)", operation, fallback)
    return fallback


# ── Platform ─────────────────────────────────────────────────────────────


class TwitterPlatform(Platform):
    name = "twitter"
    display_name = "Twitter/X"
    icon = "🐦"
    base_referer = "https://x.com/"
    cookie_domain = ".x.com"
    required_cookies = ["auth_token", "ct0"]

    LOGIN_URL = "https://x.com/i/flow/login"
    SUCCESS_URL = "x.com/home"

    def login(self, account: str = "default", **kwargs) -> bool:
        from rich.console import Console
        console = Console(stderr=True)

        if self.login_with_browser_cookies(account):
            cookies = load_cookies(self.name, account) or []
            console.print(f"[green]✔ Extracted {len(cookies)} Twitter cookies from local browser[/green]")
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
        return "auth_token" in names and "ct0" in names

    def _get_headers(self, account: str = "default") -> dict:
        """Build Twitter API headers with bearer token + CSRF."""
        cookies = load_cookies(self.name, account) or []
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if "name" in c)
        ct0 = next((c["value"] for c in cookies if c.get("name") == "ct0"), "")

        headers = {
            "User-Agent": self.default_ua,
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Client-Language": "en",
            "Referer": "https://x.com/",
            "Origin": "https://x.com",
        }
        if cookie_str:
            headers["Cookie"] = cookie_str
        if ct0:
            headers["X-Csrf-Token"] = ct0
        return headers

    def _graphql_get(self, operation: str, variables: dict, headers: dict) -> dict | None:
        """Execute a GraphQL GET request. Uses curl_cffi if available (TLS fingerprint)."""
        query_id = _resolve_query_id(operation)
        if not query_id:
            logger.warning("twitter: cannot resolve %s queryId", operation)
            return None

        features = {k: v for k, v in _FEATURES.items() if v is not False}
        url = "%s/%s/%s?variables=%s&features=%s" % (
            GRAPHQL_URL, query_id, operation,
            urllib.parse.quote(json.dumps(variables, separators=(",", ":"))),
            urllib.parse.quote(json.dumps(features, separators=(",", ":"))),
        )

        # Prefer curl_cffi (TLS fingerprint) over httpx (blocked by Cloudflare)
        try:
            from curl_cffi import requests as cffi_requests
            resp = cffi_requests.get(url, headers=headers, impersonate="chrome", timeout=15)
            logger.debug("twitter %s (curl_cffi): %d, len=%d", operation, resp.status_code, len(resp.content))
            if resp.status_code == 200 and resp.content:
                return resp.json()
            if resp.text:
                logger.debug("twitter %s body: %s", operation, resp.text[:200])
            return None
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("twitter %s curl_cffi error: %s", operation, exc)

        # Fallback to httpx (may get 404 due to TLS fingerprint)
        try:
            resp = httpx.get(url, headers=headers, timeout=15)
            logger.debug("twitter %s (httpx): %d", operation, resp.status_code)
            if resp.status_code == 200 and resp.content:
                return resp.json()
            return None
        except Exception as exc:
            logger.debug("twitter %s httpx error: %s", operation, exc)
            return None

    # ── Search ───────────────────────────────────────────────────────────

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search Twitter via GraphQL SearchTimeline."""
        headers = self._get_headers(account)
        if "Cookie" not in headers:
            logger.debug("twitter search: no cookies, skipping")
            return []

        count = kwargs.get("count", 20)
        variables = {
            "rawQuery": query,
            "count": count,
            "querySource": "typed_query",
            "product": "Latest",
        }

        try:
            data = self._graphql_get("SearchTimeline", variables, headers)
            results = []
            if data:
                entries = _extract_entries(data)
                for entry in entries[:count]:
                    tweet = _parse_tweet_entry(entry)
                    if tweet:
                        results.append(tweet)
            return results
        except Exception as exc:
            logger.debug("twitter search: %s", exc)
            return []

    # ── Trending ─────────────────────────────────────────────────────────

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get Twitter/X trending topics via guide.json."""
        headers = self._get_headers(account)
        if "Cookie" not in headers:
            logger.debug("twitter trending: no cookies, skipping")
            return []

        params = {
            "include_profile_interstitial_type": "1",
            "include_blocking": "1",
            "include_blocked_by": "1",
            "include_followed_by": "1",
            "include_want_retweets": "1",
            "include_mute_edge": "1",
            "include_can_dm": "1",
            "include_can_media_tag": "1",
            "include_ext_is_blue_verified": "1",
            "include_ext_verified_type": "1",
            "count": "20",
            "candidate_source": "trends",
            "include_page_configuration": "false",
            "entity_tokens": "false",
        }

        try:
            resp = httpx.get(TRENDING_URL, params=params, headers=headers, timeout=15)
            logger.debug("twitter trending: %d", resp.status_code)
            items = []

            if resp.status_code == 200:
                data = resp.json()
                entries = data.get("timeline", {}).get("instructions", [])
                rank = 0

                for instruction in entries:
                    for entry in instruction.get("addEntries", {}).get("entries", []):
                        content = entry.get("content", {})
                        items_list = content.get("timelineModule", {}).get("items", [])
                        for item in items_list:
                            trend = item.get("item", {}).get("content", {}).get("trend", {})
                            if trend.get("name"):
                                rank += 1
                                tweet_count = trend.get("trendMetadata", {}).get("metaDescription", "")
                                items.append(TrendingItem(
                                    rank=rank,
                                    title=trend["name"],
                                    url=f"https://x.com/search?q={urllib.parse.quote(trend['name'])}",
                                    hot_value=tweet_count,
                                ))
            else:
                logger.warning("twitter trending: HTTP %d", resp.status_code)

            return items
        except Exception as exc:
            logger.debug("twitter trending: %s", exc)
            return []

    # ── Publish ──────────────────────────────────────────────────────────

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish tweet via GraphQL CreateTweet mutation."""
        headers = self._get_headers(account)

        tweet_text = content.text
        if content.title and content.title not in tweet_text:
            tweet_text = f"{content.title}\n\n{tweet_text}"

        query_id = _resolve_query_id("CreateTweet")
        if not query_id:
            return PublishResult(success=False, platform=self.name, error="Cannot resolve CreateTweet queryId")

        variables = {
            "tweet_text": tweet_text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
        }

        payload = {
            "variables": json.dumps(variables),
            "features": json.dumps(
                {k: v for k, v in _FEATURES.items() if v is not False},
            ),
            "queryId": query_id,
        }

        try:
            resp = httpx.post(
                f"{GRAPHQL_URL}/{query_id}/CreateTweet",
                headers=headers,
                data=payload,
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                tweet_result = (
                    data.get("data", {})
                    .get("create_tweet", {})
                    .get("tweet_results", {})
                    .get("result", {})
                )
                tweet_id = tweet_result.get("rest_id", "")
                return PublishResult(
                    success=True,
                    platform=self.name,
                    post_id=tweet_id,
                    url=f"https://x.com/i/status/{tweet_id}" if tweet_id else "",
                )
            else:
                return PublishResult(
                    success=False, platform=self.name,
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))

    # ── CLI subgroup ─────────────────────────────────────────────────────

    @property
    def cli_group(self):
        platform = self  # capture for closures

        @click.group(name="twitter")
        def twitter_group():
            """🐦 Twitter/X — search, publish, trending"""
            pass

        @twitter_group.command()
        @click.argument("query")
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def search(query, count, as_json, account):
            """Search Twitter/X."""
            from socialcli.utils.output import print_json, print_table
            results = platform.search(query, account, count=count)
            if as_json:
                print_json([r.__dict__ for r in results])
            else:
                rows = [[r.title[:50], r.author, str(r.likes), r.url] for r in results]
                print_table(f"🔍 Search: {query}", ["Tweet", "Author", "Likes", "URL"], rows)

        @twitter_group.command()
        @click.option("--count", "-n", default=20)
        @click.option("--json", "as_json", is_flag=True)
        @click.option("--account", "-a", default="default")
        def trending(count, as_json, account):
            """Get Twitter/X trending topics."""
            from socialcli.utils.output import print_json, print_table
            items = platform.trending(account)[:count]
            if as_json:
                print_json([t.__dict__ for t in items])
            else:
                rows = [[str(t.rank), t.title, t.hot_value] for t in items]
                print_table("🔥 Twitter/X Trending", ["#", "Topic", "Tweets"], rows)

        @twitter_group.command()
        @click.argument("text")
        @click.option("--image", "-i", multiple=True)
        @click.option("--account", "-a", default="default")
        def publish(text, image, account):
            """Publish a tweet."""
            from socialcli.utils import output
            c = Content(text=text, images=list(image))
            result = platform.publish(c, account)
            if result.success:
                output.success(f"Tweet posted: {result.url}")
            else:
                output.error(f"Tweet failed: {result.error}")

        return twitter_group


# ── Helpers ──────────────────────────────────────────────────────────────


def _extract_entries(data: dict) -> list:
    """Extract timeline entries from GraphQL search response."""
    try:
        instructions = (
            data.get("data", {})
            .get("search_by_raw_query", {})
            .get("search_timeline", {})
            .get("timeline", {})
            .get("instructions", [])
        )
        for inst in instructions:
            entries = inst.get("entries", [])
            if entries:
                return entries
    except Exception:
        pass
    return []


def _parse_tweet_entry(entry: dict) -> SearchResult | None:
    """Parse a single tweet entry from timeline."""
    try:
        content = entry.get("content", {})
        item = content.get("itemContent", {})
        result = item.get("tweet_results", {}).get("result", {})

        if result.get("__typename") == "TweetWithVisibilityResults":
            result = result.get("tweet", result)

        core = result.get("core", {}).get("user_results", {}).get("result", {})
        legacy = result.get("legacy", {})
        user_legacy = core.get("legacy", {})

        text = legacy.get("full_text", "")
        tweet_id = legacy.get("id_str", result.get("rest_id", ""))
        screen_name = user_legacy.get("screen_name", "")

        if not text and not screen_name:
            return None

        return SearchResult(
            title=text[:200],
            url=f"https://x.com/{screen_name}/status/{tweet_id}" if screen_name else "",
            author=f"@{screen_name}" if screen_name else "",
            likes=legacy.get("favorite_count", 0),
            comments=legacy.get("reply_count", 0),
            created_at=legacy.get("created_at", ""),
        )
    except Exception:
        return None
