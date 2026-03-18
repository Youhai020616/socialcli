"""Smoke tests for Bilibili platform — public API, no login required."""
from __future__ import annotations

import pytest
from socialcli.platforms.bilibili.client import BilibiliPlatform

pytestmark = pytest.mark.network  # All tests in this file need network


@pytest.fixture
def bilibili():
    return BilibiliPlatform()


def test_bilibili_trending_returns_data(bilibili):
    items = bilibili.trending()
    assert len(items) > 0
    assert items[0].title
    assert items[0].url
    assert items[0].rank == 1
    assert "bilibili.com" in items[0].url


def test_bilibili_trending_has_metadata(bilibili):
    items = bilibili.trending()
    first = items[0]
    assert first.hot_value  # e.g. "123456 views"
    assert "views" in first.hot_value
    assert first.category  # e.g. "搞笑"


@pytest.mark.flaky_network
def test_bilibili_search_returns_data(bilibili):
    """May fail due to Bilibili rate limiting on search API."""
    results = bilibili.search("编程", count=5)
    assert len(results) > 0
    assert results[0].title
    assert results[0].url
    assert "bilibili.com" in results[0].url


@pytest.mark.flaky_network
def test_bilibili_search_has_author(bilibili):
    """May fail due to Bilibili rate limiting on search API."""
    results = bilibili.search("Python教程", count=5)
    assert len(results) > 0
    assert results[0].author  # UP主 name


@pytest.mark.flaky_network
def test_bilibili_search_count_limit(bilibili):
    results = bilibili.search("音乐", count=5)
    assert len(results) <= 5
