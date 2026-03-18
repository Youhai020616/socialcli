"""Unit tests for scheduler — pure logic, uses tmp file."""
from __future__ import annotations

import pytest
from socialcli.platforms.base import Content
from socialcli.core import scheduler


@pytest.fixture(autouse=True)
def use_tmp_schedule(tmp_path, monkeypatch):
    """Redirect schedule file to tmp dir."""
    monkeypatch.setattr(scheduler, "SCHEDULE_FILE", tmp_path / "schedule.json")


def _content(**kwargs):
    defaults = {"title": "Test", "text": "Hello"}
    defaults.update(kwargs)
    return Content(**defaults)


class TestAddAndList:
    def test_add_task(self):
        task = scheduler.add_task(_content(), ["twitter"], "2030-01-01T00:00:00")
        assert task["id"]
        assert task["status"] == "pending"
        assert task["platforms"] == ["twitter"]

    def test_list_tasks(self):
        scheduler.add_task(_content(), ["twitter"], "2030-01-01T00:00:00")
        scheduler.add_task(_content(), ["reddit"], "2030-06-01T00:00:00")
        tasks = scheduler.list_tasks()
        assert len(tasks) == 2

    def test_list_tasks_filter_by_status(self):
        scheduler.add_task(_content(), ["twitter"], "2030-01-01T00:00:00")
        assert len(scheduler.list_tasks("pending")) == 1
        assert len(scheduler.list_tasks("published")) == 0


class TestRemove:
    def test_remove_existing(self):
        task = scheduler.add_task(_content(), ["twitter"], "2030-01-01T00:00:00")
        assert scheduler.remove_task(task["id"]) is True
        assert len(scheduler.list_tasks()) == 0

    def test_remove_nonexistent(self):
        assert scheduler.remove_task("nonexistent") is False


class TestDueTasks:
    def test_past_time_is_due(self):
        scheduler.add_task(_content(), ["twitter"], "2020-01-01T00:00:00")
        due = scheduler.get_due_tasks()
        assert len(due) == 1

    def test_future_time_not_due(self):
        scheduler.add_task(_content(), ["twitter"], "2099-01-01T00:00:00")
        due = scheduler.get_due_tasks()
        assert len(due) == 0

    def test_only_pending_tasks_are_due(self):
        task = scheduler.add_task(_content(), ["twitter"], "2020-01-01T00:00:00")
        scheduler.mark_task(task["id"], "published")
        due = scheduler.get_due_tasks()
        assert len(due) == 0


class TestMarkTask:
    def test_mark_published(self):
        task = scheduler.add_task(_content(), ["twitter"], "2020-01-01T00:00:00")
        scheduler.mark_task(task["id"], "published")
        tasks = scheduler.list_tasks()
        assert tasks[0]["status"] == "published"
        assert tasks[0]["published_at"] is not None

    def test_mark_failed_with_error(self):
        task = scheduler.add_task(_content(), ["twitter"], "2020-01-01T00:00:00")
        scheduler.mark_task(task["id"], "failed", "Connection timeout")
        tasks = scheduler.list_tasks()
        assert tasks[0]["status"] == "failed"
        assert tasks[0]["error"] == "Connection timeout"
