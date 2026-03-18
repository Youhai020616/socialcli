"""Output formatting utilities."""
from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console(stderr=True)
stdout = Console()


def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    stdout.print_json(json.dumps(data, ensure_ascii=False, default=str))


def print_table(title: str, columns: list[str], rows: list[list]) -> None:
    """Print a table to stderr."""
    table = Table(title=title, show_header=True)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(c) for c in row])
    console.print(table)


def success(msg: str) -> None:
    console.print(f"[green]✔[/green] {msg}")


def error(msg: str) -> None:
    console.print(f"[red]✖[/red] {msg}")


def warn(msg: str) -> None:
    console.print(f"[yellow]⚠[/yellow] {msg}")


def info(msg: str) -> None:
    console.print(f"[blue]ℹ[/blue] {msg}")


def dim(msg: str) -> None:
    console.print(f"[dim]{msg}[/dim]")
