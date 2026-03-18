"""Tests for Platform base class methods."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from socialcli.platforms.base import Platform, Content, PublishResult, SearchResult, AccountInfo
from socialcli.auth import cookie_store


class ConcretePlatform(Platform):
    """Minimal concrete implementation for testing base class."""
    name = "testplat"
    display_name = "Test Platform"
    icon = "🧪"
    cookie_domain = ".test.com"
    required_cookies = ["session_id"]
    base_referer = "https://test.com/"

    def login(self, account="default", **kw): return True
    def check_login(self, account="default"): return True
    def publish(self, content, account="default"):
        return PublishResult(success=True, platform=self.name)
    def search(self, query, account="default", **kw): return []


@pytest.fixture
def plat():
    return ConcretePlatform()


@pytest.fixture(autouse=True)
def tmp_cookies(tmp_path, monkeypatch):
    monkeypatch.setattr(cookie_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cookie_store, "ACCOUNTS_DIR", tmp_path / "accounts")


class TestGetHeaders:
    def test_basic_headers(self, plat):
        headers = plat._get_headers()
        assert "User-Agent" in headers
        assert headers.get("Referer") == "https://test.com/"
        assert "Cookie" not in headers  # no cookies saved

    def test_with_cookies(self, plat):
        cookie_store.save_cookies("testplat", [
            {"name": "session_id", "value": "abc123", "domain": ".test.com"},
        ])
        headers = plat._get_headers()
        assert "Cookie" in headers
        assert "session_id=abc123" in headers["Cookie"]

    def test_no_referer(self):
        class NoRefPlatform(ConcretePlatform):
            base_referer = ""
        headers = NoRefPlatform()._get_headers()
        assert "Referer" not in headers


class TestMe:
    def test_me_no_login(self, plat):
        info = plat.me()
        assert info.platform == "testplat"
        assert info.is_logged_in is False

    def test_me_with_saved_account(self, plat):
        cookie_store.save_cookies("testplat", [{"name": "s", "value": "v"}],
                                  nickname="TestUser", user_id="uid1")
        info = plat.me()
        assert info.is_logged_in is True
        assert info.nickname == "TestUser"
        assert info.user_id == "uid1"


class TestLoginWithBrowserCookies:
    def test_success_with_mock(self, plat):
        mock_jar = MagicMock()
        mock_cookie = MagicMock()
        mock_cookie.name = "session_id"
        mock_cookie.value = "test123"
        mock_jar.__iter__ = MagicMock(return_value=iter([mock_cookie]))

        with patch("socialcli.platforms.base.Platform._extract_browser_cookies",
                   return_value={"session_id": "test123"}):
            result = plat.login_with_browser_cookies()
        assert result is True
        cookies = cookie_store.load_cookies("testplat")
        assert cookies is not None
        assert any(c["name"] == "session_id" for c in cookies)

    def test_fail_no_required_cookies(self, plat):
        with patch("socialcli.platforms.base.Platform._extract_browser_cookies",
                   return_value=None):
            result = plat.login_with_browser_cookies()
        assert result is False


class TestOptionalMethods:
    def test_trending_raises(self, plat):
        with pytest.raises(NotImplementedError):
            plat.trending()

    def test_like_raises(self, plat):
        with pytest.raises(NotImplementedError):
            plat.like("id")

    def test_comment_raises(self, plat):
        with pytest.raises(NotImplementedError):
            plat.comment("id", "text")
