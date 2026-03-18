"""
Scheduler — schedule posts for future publishing.

Storage: ~/.socialcli/schedule.json
Execution: `social schedule run` starts a background loop
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from socialcli.platforms.base import Content

SCHEDULE_FILE = Path.home() / ".socialcli" / "schedule.json"


def _load() -> list[dict]:
    if not SCHEDULE_FILE.exists():
        return []
    try:
        return json.loads(SCHEDULE_FILE.read_text())
    except Exception:
        return []


def _save(tasks: list[dict]) -> None:
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))


def add_task(
    content: Content,
    platforms: List[str],
    schedule_time: str,
    account: str = "default",
) -> dict:
    """Add a scheduled publish task."""
    tasks = _load()

    task = {
        "id": str(uuid.uuid4())[:8],
        "content": {
            "title": content.title,
            "text": content.text,
            "images": content.images,
            "video": content.video,
            "link": content.link,
            "tags": content.tags,
            "extras": content.extras,
        },
        "platforms": platforms,
        "account": account,
        "schedule_time": schedule_time,
        "status": "pending",  # pending / published / failed
        "created_at": datetime.now(timezone.utc).isoformat(),
        "published_at": None,
        "error": None,
    }

    tasks.append(task)
    _save(tasks)
    return task


def list_tasks(status: str = "") -> list[dict]:
    """List all scheduled tasks, optionally filtered by status."""
    tasks = _load()
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    return tasks


def remove_task(task_id: str) -> bool:
    """Remove a scheduled task by ID."""
    tasks = _load()
    original = len(tasks)
    tasks = [t for t in tasks if t.get("id") != task_id]
    if len(tasks) < original:
        _save(tasks)
        return True
    return False


def get_due_tasks() -> list[dict]:
    """Get tasks that are due for publishing."""
    tasks = _load()
    now = datetime.now(timezone.utc)
    due = []

    for task in tasks:
        if task.get("status") != "pending":
            continue
        try:
            scheduled = datetime.fromisoformat(task["schedule_time"])
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=timezone.utc)
            if scheduled <= now:
                due.append(task)
        except (ValueError, KeyError):
            continue

    return due


def mark_task(task_id: str, status: str, error: str = "") -> None:
    """Update task status."""
    tasks = _load()
    for task in tasks:
        if task.get("id") == task_id:
            task["status"] = status
            if status == "published":
                task["published_at"] = datetime.now(timezone.utc).isoformat()
            if error:
                task["error"] = error
            break
    _save(tasks)


def run_due_tasks() -> list[dict]:
    """Execute all due tasks. Returns results."""
    from socialcli.platforms import registry
    from socialcli.core.publisher import publish_all

    registry.load_all()

    due = get_due_tasks()
    results = []

    for task in due:
        content = Content(
            title=task["content"].get("title", ""),
            text=task["content"].get("text", ""),
            images=task["content"].get("images", []),
            video=task["content"].get("video", ""),
            link=task["content"].get("link", ""),
            tags=task["content"].get("tags", []),
            extras=task["content"].get("extras", {}),
        )

        try:
            publish_results = publish_all(
                content,
                task["platforms"],
                account=task.get("account", "default"),
            )
            success = all(r.success for r in publish_results)
            errors = "; ".join(r.error for r in publish_results if r.error)

            mark_task(task["id"], "published" if success else "failed", errors)
            results.append({"task_id": task["id"], "success": success, "errors": errors})
        except Exception as e:
            mark_task(task["id"], "failed", str(e))
            results.append({"task_id": task["id"], "success": False, "errors": str(e)})

    return results
