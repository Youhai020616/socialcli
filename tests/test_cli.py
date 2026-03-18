"""CLI integration tests — invoke commands via Click test runner."""
from __future__ import annotations

import pytest
from click.testing import CliRunner
from socialcli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestBasicCommands:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "socialcli" in result.output.lower() or "social" in result.output.lower()

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_accounts_no_login(self, runner):
        result = runner.invoke(cli, ["accounts"])
        assert result.exit_code == 0

    def test_publish_no_platforms(self, runner):
        result = runner.invoke(cli, ["publish", "Hello"])
        assert result.exit_code == 1  # Should error without -p

    def test_publish_no_content(self, runner):
        result = runner.invoke(cli, ["publish", "-p", "reddit"])
        assert result.exit_code == 1  # Should error with no content


class TestDryRun:
    def test_dry_run_single_platform(self, runner):
        result = runner.invoke(cli, [
            "publish", "Test message", "-p", "reddit", "--dry-run",
        ])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output or "Dry Run" in result.output

    def test_dry_run_multiple_platforms(self, runner):
        result = runner.invoke(cli, [
            "publish", "Test", "-p", "reddit,twitter,bilibili", "--dry-run",
        ])
        assert result.exit_code == 0
        assert "3" in result.output  # "3/3 platforms"

    def test_dry_run_with_title_and_tags(self, runner):
        result = runner.invoke(cli, [
            "publish", "Body text",
            "-t", "My Title",
            "--tags", "tag1,tag2",
            "-p", "twitter",
            "--dry-run",
        ])
        assert result.exit_code == 0
        assert "My Title" in result.output


class TestPlatformSubcommands:
    def test_reddit_search(self, runner):
        result = runner.invoke(cli, ["reddit", "search", "python", "-n", "2", "--json"])
        assert result.exit_code == 0
        # Should return JSON array
        assert "[" in result.output

    def test_reddit_trending(self, runner):
        result = runner.invoke(cli, ["reddit", "trending", "-n", "2", "--json"])
        assert result.exit_code == 0
        assert "rank" in result.output

    def test_bilibili_trending(self, runner):
        result = runner.invoke(cli, ["bilibili", "trending", "-n", "2", "--json"])
        assert result.exit_code == 0
        assert "rank" in result.output

    def test_douyin_trending_no_crash(self, runner):
        result = runner.invoke(cli, ["douyin", "trending", "--json"])
        assert result.exit_code == 0  # Should not crash, may return []


class TestSchedule:
    def test_schedule_publish(self, runner):
        result = runner.invoke(cli, [
            "publish", "Scheduled post",
            "-p", "reddit", "-r", "test",
            "--schedule", "2030-06-01T12:00:00",
        ])
        assert result.exit_code == 0
        assert "Scheduled" in result.output

    def test_schedule_list(self, runner):
        result = runner.invoke(cli, ["schedule", "list"])
        assert result.exit_code == 0

    def test_schedule_run(self, runner):
        result = runner.invoke(cli, ["schedule", "run"])
        assert result.exit_code == 0


class TestConfig:
    def test_config_show_empty(self, runner):
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0

    def test_config_set_and_get(self, runner, tmp_path, monkeypatch):
        from socialcli.commands import config as config_mod
        monkeypatch.setattr(config_mod, "CONFIG_FILE", tmp_path / "config.json")

        result = runner.invoke(cli, ["config", "set", "test_key", "test_value"])
        assert result.exit_code == 0
        assert "test_key" in result.output

        result = runner.invoke(cli, ["config", "get", "test_key"])
        assert result.exit_code == 0
        assert "test_value" in result.output

    def test_config_unset(self, runner, tmp_path, monkeypatch):
        from socialcli.commands import config as config_mod
        monkeypatch.setattr(config_mod, "CONFIG_FILE", tmp_path / "config.json")

        runner.invoke(cli, ["config", "set", "k", "v"])
        result = runner.invoke(cli, ["config", "unset", "k"])
        assert result.exit_code == 0
        assert "Removed" in result.output


class TestLogout:
    def test_logout_no_session(self, runner):
        result = runner.invoke(cli, ["logout", "nonexistent_platform"])
        assert result.exit_code == 0
        assert "No saved session" in result.output


class TestTrending:
    def test_aggregated_trending(self, runner):
        result = runner.invoke(cli, ["trending", "-p", "reddit,bilibili", "-n", "2", "--json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "reddit" in data or "bilibili" in data

    def test_trending_single_platform(self, runner):
        result = runner.invoke(cli, ["trending", "-p", "reddit", "-n", "2", "--json"])
        assert result.exit_code == 0


class TestHistory:
    def test_history_empty(self, runner):
        result = runner.invoke(cli, ["history"])
        assert result.exit_code == 0

    def test_history_json(self, runner):
        result = runner.invoke(cli, ["history", "--json"])
        assert result.exit_code == 0


class TestPublishFromFile:
    def test_markdown_file(self, runner, tmp_path):
        md = tmp_path / "post.md"
        md.write_text("# My Title\n\nBody paragraph here.")
        result = runner.invoke(cli, [
            "publish", "-f", str(md), "-p", "reddit", "--dry-run",
        ])
        assert result.exit_code == 0
        assert "My Title" in result.output
        assert "Dry Run" in result.output

    def test_missing_file(self, runner):
        result = runner.invoke(cli, ["publish", "-f", "/nonexistent.md", "-p", "reddit"])
        assert result.exit_code == 1
