"""Unit tests for content_adapter — pure logic, no network."""
from __future__ import annotations

import pytest
from socialcli.platforms.base import Content
from socialcli.core.content_adapter import adapt, validate, PLATFORM_RULES


def _content(**kwargs):
    return Content(**kwargs)


class TestAdapt:
    def test_twitter_truncates_to_280(self):
        c = _content(text="a" * 500)
        adapted = adapt(c, "twitter")
        assert len(adapted.text) <= 280

    def test_twitter_merges_title_to_text(self):
        c = _content(title="My Title", text="Body text")
        adapted = adapt(c, "twitter")
        assert adapted.title == ""
        assert "My Title" in adapted.text
        assert "Body text" in adapted.text

    def test_reddit_keeps_title_separate(self):
        c = _content(title="My Title", text="Body")
        adapted = adapt(c, "reddit")
        assert adapted.title == "My Title"
        assert adapted.text == "Body"

    def test_reddit_truncates_long_title(self):
        c = _content(title="x" * 500, text="body")
        adapted = adapt(c, "reddit")
        assert len(adapted.title) <= 300
        assert adapted.title.endswith("...")

    def test_tags_appended_to_text(self):
        c = _content(text="Hello", tags=["coding", "AI"])
        adapted = adapt(c, "twitter")
        assert "#coding" in adapted.text
        assert "#AI" in adapted.text

    def test_link_appended_for_twitter(self):
        c = _content(text="Check this", link="https://example.com")
        adapted = adapt(c, "twitter")
        assert "https://example.com" in adapted.text

    def test_douyin_title_truncated(self):
        c = _content(title="这是一个非常长的标题测试超过三十个字符的情况下会怎么处理", text="desc")
        adapted = adapt(c, "douyin")
        assert len(adapted.title) <= 30

    def test_empty_content_passes_through(self):
        c = _content()
        adapted = adapt(c, "twitter")
        assert adapted.text == ""
        assert adapted.title == ""

    def test_unknown_platform_uses_defaults(self):
        c = _content(title="Title", text="Body")
        adapted = adapt(c, "nonexistent_platform")
        assert adapted.title == "Title"
        assert adapted.text == "Body"


class TestValidate:
    def test_tiktok_warns_missing_video(self):
        c = _content(text="Hello")
        warnings = validate(c, "tiktok")
        assert any("video" in w.lower() for w in warnings)

    def test_reddit_warns_missing_subreddit(self):
        c = _content(text="Hello")
        warnings = validate(c, "reddit")
        assert any("subreddit" in w.lower() for w in warnings)

    def test_empty_content_warns(self):
        c = _content()
        warnings = validate(c, "twitter")
        assert any("empty" in w.lower() for w in warnings)

    def test_valid_twitter_no_warnings(self):
        c = _content(text="Hello world")
        warnings = validate(c, "twitter")
        assert warnings == []

    def test_all_platforms_have_rules(self):
        """Every platform in PLATFORM_RULES should be adaptable."""
        c = _content(title="T", text="Body", tags=["tag1"])
        for name in PLATFORM_RULES:
            adapted = adapt(c, name)
            assert isinstance(adapted, Content)
