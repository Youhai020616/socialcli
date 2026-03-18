"""social history — view publish history."""
from __future__ import annotations

import json
from pathlib import Path

import click

from socialcli.utils import output
from socialcli.utils.output import console, print_json

HISTORY_FILE = Path.home() / ".socialcli" / "history.jsonl"


@click.command()
@click.option("--count", "-n", default=20, help="Number of entries to show")
@click.option("--platform", "-p", default="", help="Filter by platform")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def history(count, platform, as_json):
    """View publish history.

    Examples:

        social history

        social history -n 5 -p reddit

        social history --json
    """
    if not HISTORY_FILE.exists():
        output.info("No publish history yet.")
        return

    entries = []
    for line in HISTORY_FILE.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if platform and entry.get("platform") != platform:
                continue
            entries.append(entry)
        except json.JSONDecodeError:
            continue

    entries = entries[-count:]  # Last N entries

    if as_json:
        print_json(entries)
        return

    if not entries:
        output.info("No matching history entries.")
        return

    from rich.table import Table
    table = Table(title=f"Publish History (last {len(entries)})", show_header=True)
    table.add_column("Time", width=19)
    table.add_column("Platform", style="cyan")
    table.add_column("Status")
    table.add_column("Title / Text")
    table.add_column("URL")

    for e in entries:
        time_str = e.get("time", "")[:19].replace("T", " ")
        status = "[green]✔[/green]" if e.get("success") else "[red]✖[/red]"
        title = e.get("title") or e.get("text", "")[:40]
        url = e.get("url", "")
        if url and len(url) > 50:
            url = url[:47] + "..."
        table.add_row(time_str, e.get("platform", ""), status, title[:40], url)

    console.print(table)
