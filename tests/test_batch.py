"""Unit tests for batch loader — pure logic, uses tmp files."""
from __future__ import annotations

import csv
import json
import pytest
from pathlib import Path

from socialcli.core.batch import (
    load_tasks_from_csv,
    load_tasks_from_json,
    load_tasks_from_directory,
)


class TestLoadFromCSV:
    def test_basic_csv(self, tmp_path):
        f = tmp_path / "posts.csv"
        f.write_text(
            "platform,title,content,image,video,tags,subreddit\n"
            "twitter,,Hello from CSV!,photo.jpg,,coding,\n"
            "reddit,My Post,Body text,,,,programming\n"
        )
        tasks = load_tasks_from_csv(str(f))
        assert len(tasks) == 2

        assert tasks[0]["platforms"] == ["twitter"]
        assert tasks[0]["content"].text == "Hello from CSV!"
        assert tasks[0]["content"].images == ["photo.jpg"]

        assert tasks[1]["platforms"] == ["reddit"]
        assert tasks[1]["content"].title == "My Post"
        assert tasks[1]["content"].extras["subreddit"] == "programming"

    def test_csv_with_multiple_platforms(self, tmp_path):
        f = tmp_path / "multi.csv"
        f.write_text(
            "platform,title,content,image,video,tags,subreddit\n"
            "twitter,reddit,,Cross post,,,,\n"
        )
        tasks = load_tasks_from_csv(str(f))
        # "twitter,reddit" in platform column → split
        # But CSV format puts "twitter" as platform, "reddit" would be ambiguous
        # The current parser splits on comma within the platform field
        assert len(tasks) == 1

    def test_csv_with_tags(self, tmp_path):
        f = tmp_path / "tags.csv"
        f.write_text(
            "platform,title,content,image,video,tags,subreddit\n"
            "douyin,标题,描述,,video.mp4,美食;分享,\n"
        )
        tasks = load_tasks_from_csv(str(f))
        assert tasks[0]["content"].tags == ["美食", "分享"]
        assert tasks[0]["content"].video == "video.mp4"

    def test_csv_with_schedule(self, tmp_path):
        f = tmp_path / "sched.csv"
        f.write_text(
            "platform,title,content,image,video,tags,subreddit,schedule\n"
            "twitter,,Hello,,,,,2030-01-01T09:00:00\n"
        )
        tasks = load_tasks_from_csv(str(f))
        assert tasks[0]["schedule"] == "2030-01-01T09:00:00"


class TestLoadFromJSON:
    def test_basic_json_list(self, tmp_path):
        f = tmp_path / "posts.json"
        data = [
            {"title": "Post 1", "text": "Hello", "platforms": "twitter,reddit"},
            {"title": "Post 2", "content": "World", "platforms": ["bilibili"]},
        ]
        f.write_text(json.dumps(data))
        tasks = load_tasks_from_json(str(f))
        assert len(tasks) == 2
        assert tasks[0]["platforms"] == ["twitter", "reddit"]
        assert tasks[0]["content"].title == "Post 1"
        assert tasks[1]["platforms"] == ["bilibili"]
        assert tasks[1]["content"].text == "World"

    def test_single_json_object(self, tmp_path):
        f = tmp_path / "single.json"
        data = {"title": "Solo", "text": "One post", "platforms": ["twitter"]}
        f.write_text(json.dumps(data))
        tasks = load_tasks_from_json(str(f))
        assert len(tasks) == 1
        assert tasks[0]["content"].title == "Solo"

    def test_json_with_extras(self, tmp_path):
        f = tmp_path / "extras.json"
        data = [{"text": "Hi", "platforms": ["reddit"], "extras": {"subreddit": "test"}}]
        f.write_text(json.dumps(data))
        tasks = load_tasks_from_json(str(f))
        assert tasks[0]["content"].extras["subreddit"] == "test"


class TestLoadFromDirectory:
    def test_markdown_files(self, tmp_path):
        (tmp_path / "post1.md").write_text("# My Title\n\nBody paragraph here.")
        (tmp_path / "post2.txt").write_text("Plain text content")
        (tmp_path / "ignored.jpg").write_bytes(b"\xff\xd8")  # non-text, skipped

        tasks = load_tasks_from_directory(str(tmp_path), ["twitter"])
        assert len(tasks) == 2

        # First file (post1.md) should extract title from heading
        md_task = next(t for t in tasks if t["content"].title == "My Title")
        assert "Body paragraph" in md_task["content"].text
        assert md_task["platforms"] == ["twitter"]

        # Second file (post2.txt) has no heading
        txt_task = next(t for t in tasks if "Plain text" in t["content"].text)
        assert txt_task["content"].title == ""

    def test_empty_directory(self, tmp_path):
        tasks = load_tasks_from_directory(str(tmp_path), ["twitter"])
        assert tasks == []

    def test_sorts_by_filename(self, tmp_path):
        (tmp_path / "02_second.md").write_text("# Second")
        (tmp_path / "01_first.md").write_text("# First")
        tasks = load_tasks_from_directory(str(tmp_path), ["reddit"])
        assert tasks[0]["content"].title == "First"
        assert tasks[1]["content"].title == "Second"
