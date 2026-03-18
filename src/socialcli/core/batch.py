"""
Batch operations — publish from CSV/JSON/directory.

CSV format:
  platform,title,content,image,video,tags,subreddit,schedule
  douyin,标题,描述,,video.mp4,tag1;tag2,,
  reddit,Title,Body text,,,,programming,
  twitter,,Tweet text,photo.jpg,,,,
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import List

from socialcli.platforms.base import Content, PublishResult
from socialcli.core.publisher import publish_all


def load_tasks_from_csv(filepath: str) -> list[dict]:
    """Load publish tasks from CSV file."""
    tasks = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            platforms = [p.strip() for p in row.get("platform", "").split(",") if p.strip()]
            tags = [t.strip() for t in row.get("tags", "").split(";") if t.strip()]
            images = [i.strip() for i in row.get("image", "").split(";") if i.strip()]

            tasks.append({
                "content": Content(
                    title=row.get("title", ""),
                    text=row.get("content", ""),
                    images=images,
                    video=row.get("video", ""),
                    tags=tags,
                    extras={"subreddit": row.get("subreddit", "")},
                ),
                "platforms": platforms,
                "schedule": row.get("schedule", ""),
            })

    return tasks


def load_tasks_from_json(filepath: str) -> list[dict]:
    """Load publish tasks from JSON file."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    tasks = []
    items = data if isinstance(data, list) else [data]

    for item in items:
        platforms = item.get("platforms", [])
        if isinstance(platforms, str):
            platforms = [p.strip() for p in platforms.split(",")]

        tasks.append({
            "content": Content(
                title=item.get("title", ""),
                text=item.get("text", item.get("content", "")),
                images=item.get("images", []),
                video=item.get("video", ""),
                link=item.get("link", ""),
                tags=item.get("tags", []),
                extras=item.get("extras", {}),
            ),
            "platforms": platforms,
            "schedule": item.get("schedule", ""),
        })

    return tasks


def load_tasks_from_directory(dirpath: str, platforms: list[str]) -> list[dict]:
    """Load tasks from a directory — each .md/.txt file is one post."""
    tasks = []
    dir_path = Path(dirpath)

    for f in sorted(dir_path.glob("*")):
        if f.suffix not in (".md", ".txt", ".markdown"):
            continue

        text = f.read_text(encoding="utf-8")
        title = ""

        # Extract title from first heading
        if f.suffix in (".md", ".markdown"):
            lines = text.split("\n")
            for line in lines:
                if line.startswith("# "):
                    title = line[2:].strip()
                    text = "\n".join(l for l in lines if l != line).strip()
                    break

        tasks.append({
            "content": Content(title=title, text=text),
            "platforms": platforms,
            "schedule": "",
        })

    return tasks


def run_batch(
    tasks: list[dict],
    account: str = "default",
    delay: float = 2.0,
    dry_run: bool = False,
) -> list[dict]:
    """Execute batch publish tasks."""
    import time
    import random

    results = []

    for i, task in enumerate(tasks):
        content = task["content"]
        platforms = task["platforms"]
        schedule = task.get("schedule", "")

        # Scheduled tasks go to scheduler
        if schedule:
            from socialcli.core.scheduler import add_task
            added = add_task(content, platforms, schedule, account)
            results.append({
                "index": i + 1,
                "type": "scheduled",
                "task_id": added["id"],
                "schedule": schedule,
                "platforms": platforms,
            })
            continue

        # Immediate publish
        publish_results = publish_all(content, platforms, account=account, dry_run=dry_run)
        results.append({
            "index": i + 1,
            "type": "published",
            "results": [{"platform": r.platform, "success": r.success, "error": r.error, "url": r.url}
                        for r in publish_results],
        })

        # Delay between tasks
        if i < len(tasks) - 1 and not dry_run:
            jitter = delay + random.uniform(0, delay * 0.5)
            time.sleep(jitter)

    return results
