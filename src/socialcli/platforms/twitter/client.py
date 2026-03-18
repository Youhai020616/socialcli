"""
Twitter/X platform client — browser cookie extraction + reverse-engineered API.

Login: extract cookies from user's Chrome browser (browser-cookie3)
       or browser login via Playwright
Publish: reverse-engineered GraphQL API
Search/Trending: reverse-engineered API endpoints
"""
from __future__ import annotations

import json
import re
from typing import List

import click
import httpx

from socialcli.platforms.base import (
    Platform, Content, PublishResult, SearchResult, TrendingItem, AccountInfo,
)
from socialcli.auth.cookie_store import (
    load_cookies, save_cookies, cookie_string, load_account_info,
)
from socialcli.auth.browser_login import browser_login

# Twitter/X API constants (reverse-engineered, ref: jackwener/twitter-cli)
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
BASE_URL = "https://x.com"
API_URL = "https://x.com/i/api"
GRAPHQL_URL = "https://x.com/i/api/graphql"

# Trending endpoint
TRENDING_URL = f"{API_URL}/2/guide.json"

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class TwitterPlatform(Platform):
    name = "twitter"
    display_name = "Twitter/X"
    icon = "🐦"

    LOGIN_URL = "https://x.com/i/flow/login"
    SUCCESS_URL = "x.com/home"

    def login(self, account: str = "default", **kwargs) -> bool:
        """Login via browser — user enters credentials, we capture cookies."""
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
        # Twitter requires auth_token and ct0 cookies
        names = {c.get("name") for c in cookies}
        return "auth_token" in names or "ct0" in names or len(cookies) > 5

    def _get_headers(self, account: str = "default") -> dict:
        """Build Twitter API headers with cookie + CSRF token."""
        cookies = load_cookies(self.name, account) or []
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if "name" in c)
        ct0 = next((c["value"] for c in cookies if c.get("name") == "ct0"), "")

        return {
            "User-Agent": DEFAULT_UA,
            "Cookie": cookie_str,
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "X-Csrf-Token": ct0,
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Client-Language": "en",
            "Referer": "https://x.com/",
            "Origin": "https://x.com",
        }

    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish tweet via reverse-engineered GraphQL API."""
        headers = self._get_headers(account)

        tweet_text = content.text
        if content.title and content.title not in tweet_text:
            tweet_text = f"{content.title}\n\n{tweet_text}"

        # CreateTweet GraphQL mutation
        variables = {
            "tweet_text": tweet_text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
        }

        # TODO: Upload media first if content.images or content.video
        # For now, text-only publishing
        if content.images:
            # Media upload would go here (multipart upload to upload.twitter.com)
            pass

        payload = {
            "variables": json.dumps(variables),
            "features": json.dumps({
                "community_tweet_creation": False,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "articles_preview_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
            }),
            "queryId": "znCbgGaBcIFDlGEhXdFVzg",  # CreateTweet
        }

        try:
            resp = httpx.post(
                f"{GRAPHQL_URL}/znCbgGaBcIFDlGEhXdFVzg/CreateTweet",
                headers=headers,
                data=payload,
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                tweet_result = data.get("data", {}).get("create_tweet", {}).get("tweet_results", {}).get("result", {})
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

    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search Twitter via adaptive search API."""
        headers = self._get_headers(account)
        count = kwargs.get("count", 20)

        variables = {
            "rawQuery": query,
            "count": count,
            "querySource": "typed_query",
            "product": "Latest",
        }

        features = {
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "view_counts_everywhere_api_enabled": True,
        }

        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(features),
        }

        try:
            resp = httpx.get(
                f"{GRAPHQL_URL}/MJpyQGqgklrVl_6rYKQbow/SearchTimeline",
                params=params,
                headers=headers,
                timeout=15,
            )

            results = []
            if resp.status_code == 200:
                data = resp.json()
                entries = _extract_entries(data)
                for entry in entries[:count]:
                    tweet = _parse_tweet_entry(entry)
                    if tweet:
                        results.append(tweet)

            return results
        except Exception:
            return []

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get Twitter/X trending topics."""
        headers = self._get_headers(account)

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
                                    url=f"https://x.com/search?q={trend['name']}",
                                    hot_value=tweet_count,
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
            nickname=info.get("nickname", ""),
            user_id=info.get("user_id", ""),
            is_logged_in=True,
        )

    # --- CLI subgroup ---
    @property
    def cli_group(self):
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
            results = _platform.search(query, account, count=count)
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
            items = _platform.trending(account)[:count]
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
            result = _platform.publish(c, account)
            if result.success:
                output.success(f"Tweet posted: {result.url}")
            else:
                output.error(f"Tweet failed: {result.error}")

        return twitter_group


# --- Tweet parsing helpers ---

def _extract_entries(data: dict) -> list:
    """Extract timeline entries from GraphQL response."""
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
    """Parse a single tweet entry."""
    try:
        content = entry.get("content", {})
        item = content.get("itemContent", {})
        result = item.get("tweet_results", {}).get("result", {})

        # Handle __typename == "TweetWithVisibilityResults"
        if result.get("__typename") == "TweetWithVisibilityResults":
            result = result.get("tweet", result)

        core = result.get("core", {}).get("user_results", {}).get("result", {})
        legacy = result.get("legacy", {})
        user_legacy = core.get("legacy", {})

        text = legacy.get("full_text", "")
        tweet_id = legacy.get("id_str", result.get("rest_id", ""))
        screen_name = user_legacy.get("screen_name", "")

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
