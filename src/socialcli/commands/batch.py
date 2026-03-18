"""social batch — batch publish from file."""
from __future__ import annotations

import click
from socialcli.utils import output


@click.command()
@click.argument("file")
@click.option("--platforms", "-p", default="", help="Default platforms (for directory mode)")
@click.option("--account", "-a", default="default")
@click.option("--delay", default=2.0, help="Delay between tasks (seconds)")
@click.option("--dry-run", is_flag=True, help="Preview without publishing")
def batch(file, platforms, account, delay, dry_run):
    """Batch publish from CSV, JSON, or directory.

    Examples:

        social batch posts.csv

        social batch posts.json --dry-run

        social batch ./posts-dir/ -p douyin,twitter
    """
    import os
    from socialcli.core.batch import (
        load_tasks_from_csv,
        load_tasks_from_json,
        load_tasks_from_directory,
        run_batch,
    )

    if not os.path.exists(file):
        output.error(f"File not found: {file}")
        raise SystemExit(1)

    # Load tasks
    if os.path.isdir(file):
        platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
        if not platform_list:
            output.error("Directory mode requires --platforms / -p")
            raise SystemExit(1)
        tasks = load_tasks_from_directory(file, platform_list)
    elif file.endswith(".csv"):
        tasks = load_tasks_from_csv(file)
    elif file.endswith(".json"):
        tasks = load_tasks_from_json(file)
    else:
        output.error(f"Unsupported file format: {file} (use .csv, .json, or directory)")
        raise SystemExit(1)

    if not tasks:
        output.info("No tasks found in file")
        return

    output.info(f"Loaded {len(tasks)} task(s) from {file}")
    if dry_run:
        output.warn("DRY RUN — nothing will be published")

    results = run_batch(tasks, account=account, delay=delay, dry_run=dry_run)

    # Summary
    published = sum(1 for r in results if r.get("type") == "published")
    scheduled = sum(1 for r in results if r.get("type") == "scheduled")
    output.success(f"Batch complete: {published} published, {scheduled} scheduled, {len(results)} total")
