"""Tests for Twitter platform — queryId resolution + parsing."""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock

from socialcli.platforms.twitter.client import (
    _resolve_query_id,
    _cached_ids,
    _FALLBACK_IDS,
    _extract_entries,
    _parse_tweet_entry,
    TwitterPlatform,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear queryId cache between tests."""
    _cached_ids.clear()
    yield
    _cached_ids.clear()


class TestQueryIdResolution:
    def test_fallback_when_github_unreachable(self):
        """Should return fallback queryId when GitHub is unreachable."""
        with patch("socialcli.platforms.twitter.client.httpx.get", side_effect=Exception("timeout")):
            qid = _resolve_query_id("SearchTimeline")
        assert qid == _FALLBACK_IDS["SearchTimeline"]

    def test_cache_hit(self):
        """Second call should use cache, not hit network."""
        _cached_ids["SearchTimeline"] = "cached_id_123"
        with patch("socialcli.platforms.twitter.client.httpx.get") as mock_get:
            qid = _resolve_query_id("SearchTimeline")
        assert qid == "cached_id_123"
        mock_get.assert_not_called()

    def test_github_source(self):
        """Should fetch from GitHub when cache is empty."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "SearchTimeline": {"queryId": "github_id_456"},
        }
        with patch("socialcli.platforms.twitter.client.httpx.get", return_value=mock_resp):
            qid = _resolve_query_id("SearchTimeline")
        assert qid == "github_id_456"
        assert _cached_ids["SearchTimeline"] == "github_id_456"

    def test_unknown_operation_returns_empty(self):
        """Unknown operation with no fallback should return empty string."""
        with patch("socialcli.platforms.twitter.client.httpx.get", side_effect=Exception("nope")):
            qid = _resolve_query_id("NonexistentOperation")
        assert qid == ""

    def test_github_resolve_actually_works(self):
        """Integration test: actually fetch from GitHub (network required)."""
        qid = _resolve_query_id("SearchTimeline")
        assert qid  # Should get some queryId
        assert len(qid) > 5  # queryIds are ~20 char base64 strings


class TestTweetParsing:
    SAMPLE_ENTRY = {
        "content": {
            "itemContent": {
                "tweet_results": {
                    "result": {
                        "__typename": "Tweet",
                        "rest_id": "123456",
                        "core": {
                            "user_results": {
                                "result": {
                                    "legacy": {
                                        "screen_name": "testuser",
                                    }
                                }
                            }
                        },
                        "legacy": {
                            "full_text": "Hello from test tweet!",
                            "id_str": "123456",
                            "favorite_count": 42,
                            "reply_count": 5,
                            "created_at": "Wed Mar 18 12:00:00 +0000 2026",
                        },
                    }
                }
            }
        }
    }

    def test_parse_tweet_entry(self):
        result = _parse_tweet_entry(self.SAMPLE_ENTRY)
        assert result is not None
        assert result.title == "Hello from test tweet!"
        assert result.author == "@testuser"
        assert result.likes == 42
        assert result.comments == 5
        assert "123456" in result.url

    def test_parse_empty_entry(self):
        result = _parse_tweet_entry({})
        assert result is None

    def test_parse_visibility_wrapper(self):
        """TweetWithVisibilityResults should be unwrapped."""
        entry = {
            "content": {
                "itemContent": {
                    "tweet_results": {
                        "result": {
                            "__typename": "TweetWithVisibilityResults",
                            "tweet": self.SAMPLE_ENTRY["content"]["itemContent"]["tweet_results"]["result"],
                        }
                    }
                }
            }
        }
        result = _parse_tweet_entry(entry)
        assert result is not None
        assert result.author == "@testuser"


class TestExtractEntries:
    def test_extract_from_search_response(self):
        data = {
            "data": {
                "search_by_raw_query": {
                    "search_timeline": {
                        "timeline": {
                            "instructions": [
                                {"entries": [{"id": "1"}, {"id": "2"}]},
                            ]
                        }
                    }
                }
            }
        }
        entries = _extract_entries(data)
        assert len(entries) == 2

    def test_extract_from_empty(self):
        assert _extract_entries({}) == []
        assert _extract_entries({"data": {}}) == []


class TestTwitterPlatform:
    def test_check_login_needs_both_cookies(self):
        """Both auth_token and ct0 are required."""
        p = TwitterPlatform()
        # No cookies
        assert p.check_login("nonexistent") is False

    def test_search_without_cookies_returns_empty(self):
        p = TwitterPlatform()
        results = p.search("test", "nonexistent_account")
        assert results == []

    def test_trending_without_cookies_returns_empty(self):
        p = TwitterPlatform()
        items = p.trending("nonexistent_account")
        assert items == []
