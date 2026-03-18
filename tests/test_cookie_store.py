"""Unit tests for cookie_store — pure logic, uses tmp_path."""
from __future__ import annotations

import json
import pytest
from socialcli.auth import cookie_store


@pytest.fixture(autouse=True)
def use_tmp_dir(tmp_path, monkeypatch):
    """Redirect cookie storage to tmp dir for all tests."""
    monkeypatch.setattr(cookie_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cookie_store, "ACCOUNTS_DIR", tmp_path / "accounts")


def _sample_cookies():
    return [
        {"name": "sid", "value": "abc123", "domain": ".example.com"},
        {"name": "token", "value": "xyz789", "domain": ".example.com"},
    ]


class TestSaveLoad:
    def test_save_and_load(self):
        cookie_store.save_cookies("testplat", _sample_cookies(), "user1", "Nick", "uid1")
        loaded = cookie_store.load_cookies("testplat", "user1")
        assert len(loaded) == 2
        assert loaded[0]["name"] == "sid"

    def test_load_nonexistent_returns_none(self):
        assert cookie_store.load_cookies("noplatform", "nouser") is None

    def test_cookie_string_format(self):
        cookie_store.save_cookies("testplat", _sample_cookies(), "user1")
        cs = cookie_store.cookie_string("testplat", "user1")
        assert "sid=abc123" in cs
        assert "token=xyz789" in cs
        assert "; " in cs

    def test_cookie_string_empty(self):
        cs = cookie_store.cookie_string("noplatform", "nouser")
        assert cs == ""


class TestAccountManagement:
    def test_list_accounts(self):
        cookie_store.save_cookies("plat1", _sample_cookies(), "a", "Alice", "1")
        cookie_store.save_cookies("plat1", _sample_cookies(), "b", "Bob", "2")
        cookie_store.save_cookies("plat2", _sample_cookies(), "c", "Charlie", "3")

        all_accts = cookie_store.list_accounts()
        assert len(all_accts) == 3

        plat1_accts = cookie_store.list_accounts("plat1")
        assert len(plat1_accts) == 2

    def test_delete_account(self):
        cookie_store.save_cookies("plat", _sample_cookies(), "user1")
        assert cookie_store.load_cookies("plat", "user1") is not None

        assert cookie_store.delete_account("plat", "user1") is True
        assert cookie_store.load_cookies("plat", "user1") is None

    def test_delete_nonexistent_returns_false(self):
        assert cookie_store.delete_account("nope", "nope") is False

    def test_load_account_info(self):
        cookie_store.save_cookies("plat", _sample_cookies(), "user1", "Nick", "uid1")
        info = cookie_store.load_account_info("plat", "user1")
        assert info["nickname"] == "Nick"
        assert info["user_id"] == "uid1"
        assert info["status"] == "active"
        assert info["login_time"]  # should be set

    def test_corrupted_json(self, tmp_path):
        path = tmp_path / "accounts" / "bad" / "user.json"
        path.parent.mkdir(parents=True)
        path.write_text("not valid json{{{")
        assert cookie_store.load_cookies("bad", "user") is None
