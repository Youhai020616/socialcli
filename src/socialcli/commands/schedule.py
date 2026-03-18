"""social schedule — manage scheduled posts."""
from __future__ import annotations

import click
from rich.table import Table

from socialcli.core import scheduler
from socialcli.utils.output import console, success, error, info


@click.group()
def schedule():
    """Manage scheduled posts."""
    pass


@schedule.command(name="list")
@click.option("--status", default="", help="Filter: pending/published/failed")
@click.option("--json", "as_json", is_flag=True)
def list_cmd(status, as_json):
    """List scheduled tasks."""
    tasks = scheduler.list_tasks(status)

    if not tasks:
        info("No scheduled tasks.")
        return

    if as_json:
        import json as _json
        click.echo(_json.dumps(tasks, ensure_ascii=False, indent=2))
        return

    table = Table(title="Scheduled Posts", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Platforms")
    table.add_column("Title")
    table.add_column("Schedule")
    table.add_column("Status")

    for t in tasks:
        title = t.get("content", {}).get("title", "") or t.get("content", {}).get("text", "")[:30]
        status_str = t.get("status", "?")
        style = "green" if status_str == "published" else "yellow" if status_str == "pending" else "red"
        table.add_row(
            t.get("id", ""),
            ",".join(t.get("platforms", [])),
            title[:30],
            t.get("schedule_time", "")[:19],
            f"[{style}]{status_str}[/{style}]",
        )

    console.print(table)


@schedule.command()
def run():
    """Execute all due scheduled tasks now."""
    info("Checking for due tasks...")
    results = scheduler.run_due_tasks()

    if not results:
        info("No due tasks.")
        return

    for r in results:
        if r["success"]:
            success(f"Task {r['task_id']} published")
        else:
            error(f"Task {r['task_id']} failed: {r['errors']}")


@schedule.command()
@click.argument("task_id")
def remove(task_id):
    """Remove a scheduled task."""
    if scheduler.remove_task(task_id):
        success(f"Task {task_id} removed")
    else:
        error(f"Task {task_id} not found")
