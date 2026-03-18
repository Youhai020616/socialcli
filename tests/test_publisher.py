"""Unit tests for publisher — uses mock platforms, no network."""
from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from socialcli.platforms.base import Content, PublishResult, Platform
from socialcli.platforms import registry
from socialcli.core import publisher


@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    """Redirect history file and ensure platforms are loaded."""
    monkeypatch.setattr(publisher, "HISTORY_FILE", tmp_path / "history.jsonl")
    registry.load_all()
    return tmp_path / "history.jsonl"


@pytest.fixture
def mock_platform(monkeypatch):
    """Register a mock platform for testing."""
    plat = MagicMock(spec=Platform)
    plat.name = "mockplat"
    plat.display_name = "MockPlatform"
    plat.icon = "🧪"
    plat.check_login.return_value = True
    plat.publish.return_value = PublishResult(
        success=True, platform="mockplat", post_id="123", url="https://mock/123",
    )

    # Temporarily register
    original = registry._platforms.copy()
    registry.register(plat)
    yield plat
    registry._platforms.clear()
    registry._platforms.update(original)


class TestDryRun:
    def test_dry_run_skips_login_check(self):
        """dry-run should work even without login."""
        results = publisher.publish_all(
            Content(text="Hello"),
            ["reddit"],
            dry_run=True,
        )
        assert len(results) == 1
        assert results[0].success is True
        assert "DRY RUN" in results[0].error

    def test_dry_run_shows_adapted_content(self):
        results = publisher.publish_all(
            Content(title="My Title", text="Body text"),
            ["twitter"],
            dry_run=True,
        )
        # Twitter merges title to text
        assert "My Title" in results[0].error

    def test_dry_run_multiple_platforms(self):
        results = publisher.publish_all(
            Content(text="Hello"),
            ["reddit", "bilibili", "twitter"],
            dry_run=True,
        )
        assert len(results) == 3
        assert all(r.success for r in results)


class TestPublish:
    def test_unknown_platform_fails(self):
        results = publisher.publish_all(
            Content(text="Hello"),
            ["nonexistent_platform"],
        )
        assert len(results) == 1
        assert results[0].success is False
        assert "Unknown platform" in results[0].error

    def test_not_logged_in_fails(self, mock_platform):
        mock_platform.check_login.return_value = False
        results = publisher.publish_all(
            Content(text="Hello"),
            ["mockplat"],
        )
        assert results[0].success is False
        assert "Not logged in" in results[0].error

    def test_successful_publish(self, mock_platform):
        results = publisher.publish_all(
            Content(text="Hello"),
            ["mockplat"],
        )
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].url == "https://mock/123"
        mock_platform.publish.assert_called_once()

    def test_publish_exception_caught(self, mock_platform):
        mock_platform.publish.side_effect = RuntimeError("API down")
        results = publisher.publish_all(
            Content(text="Hello"),
            ["mockplat"],
        )
        assert results[0].success is False
        assert "API down" in results[0].error


class TestHistory:
    def test_history_saved_on_publish(self, mock_platform, setup_env):
        history_file = setup_env
        publisher.publish_all(Content(text="Hello"), ["mockplat"])
        assert history_file.exists()
        lines = history_file.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["platform"] == "mockplat"
        assert record["success"] is True
        assert record["url"] == "https://mock/123"

    def test_no_history_on_dry_run(self, setup_env):
        history_file = setup_env
        publisher.publish_all(Content(text="Hello"), ["reddit"], dry_run=True)
        assert not history_file.exists()

    def test_no_history_on_failure(self, setup_env):
        history_file = setup_env
        publisher.publish_all(Content(text="Hello"), ["nonexistent"])
        assert not history_file.exists()
