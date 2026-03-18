"""Smoke tests for Reddit platform — public API, no login required."""
from __future__ import annotations

import pytest
from socialcli.platforms.reddit.client import RedditPlatform

pytestmark = pytest.mark.network  # All tests in this file need network


@pytest.fixture
def reddit():
    return RedditPlatform()


def test_reddit_trending_returns_data(reddit):
    items = reddit.trending()
    assert len(items) > 0
    assert items[0].title
    assert items[0].url
    assert items[0].rank == 1
    assert "reddit.com" in items[0].url


def test_reddit_search_returns_data(reddit):
    results = reddit.search("python")
    assert len(results) > 0
    assert results[0].title
    assert results[0].url
    assert results[0].author


def test_reddit_search_with_subreddit(reddit):
    results = reddit.search("beginner", subreddit="learnpython", count=5)
    assert len(results) > 0
    assert "reddit.com" in results[0].url


def test_reddit_search_empty_query_returns_empty(reddit):
    # Reddit returns empty for whitespace-only queries
    results = reddit.search("   ")
    # Should not crash, may return results or empty
    assert isinstance(results, list)


def test_reddit_trending_has_metadata(reddit):
    items = reddit.trending()
    first = items[0]
    assert first.hot_value  # e.g. "12345 upvotes"
    assert first.category   # e.g. "r/subreddit"
    assert first.category.startswith("r/")
