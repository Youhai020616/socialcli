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
