"""social status — overview of accounts, history, and scheduled tasks."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import click

from socialcli import __version__
from socialcli.auth.cookie_store import list_accounts
from socialcli.platforms import registry
from socialcli.utils.output import console


def _time_ago(iso_str: str) -> str:
    """Convert ISO timestamp to human-readable '2h ago' format."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        days = seconds // 86400
        if days == 1:
            return "yesterday"
        if days < 30:
            return f"{days}d ago"
        return f"{days // 30}mo ago"
    except Exception:
        return "—"


def _cookie_age_warning(login_time: str) -> str:
    """Return warning level based on cookie age."""
    try:
        dt = datetime.fromisoformat(login_time)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - dt).days
        if days >= 30:
            return "[red]⚠ %dd old[/red]" % days
        if days >= 7:
            return "[yellow]%dd old[/yellow]" % days
        return ""
    except Exception:
        return ""


@click.command()
def status():
    """Show SocialCLI status overview.

    Displays logged-in accounts, recent publishes, and scheduled tasks.
    """
    registry.load_all()

    console.print(f"\n  [bold]📱 SocialCLI v{__version__}[/bold]\n")

    # Accounts
    accts = list_accounts()
    if accts:
        console.print("  [bold]Accounts:[/bold]")
        for a in accts:
            plat_name = a.get("platform", "")
            acct_name = a.get("account", "default")
            login_time = a.get("login_time", "")
            time_str = _time_ago(login_time) if login_time else "—"
            age_warn = _cookie_age_warning(login_time) if login_time else ""

            # Check if platform recognizes the login
            plat = registry.get(plat_name)
            valid = plat.check_login(acct_name) if plat else False
            icon = "[green]✅[/green]" if valid else "[red]❌[/red]"

            line = f"    {icon} {plat_name:12s} ({acct_name}) — {time_str}"
            if age_warn:
                line += f"  {age_warn}"
            console.print(line)
    else:
        console.print("  [dim]No accounts. Run: social login reddit[/dim]")

    # Recent publishes
    history_file = Path.home() / ".socialcli" / "history.jsonl"
    if history_file.exists():
        lines = history_file.read_text().strip().split("\n")
        recent = []
        for line in lines[-3:]:
            try:
                recent.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        if recent:
            console.print("\n  [bold]Recent publishes:[/bold]")
            for entry in recent:
                t = entry.get("time", "")[:16].replace("T", " ")
                plat = entry.get("platform", "")
                ok = "[green]✔[/green]" if entry.get("success") else "[red]✖[/red]"
                url = entry.get("url", "")
                if url and len(url) > 45:
                    url = url[:42] + "..."
                console.print(f"    {t}  {plat:10s} {ok}  {url}")

    # Scheduled tasks
    schedule_file = Path.home() / ".socialcli" / "schedule.json"
    pending = 0
    if schedule_file.exists():
        try:
            tasks = json.loads(schedule_file.read_text())
            pending = sum(1 for t in tasks if t.get("status") == "pending")
        except Exception:
            pass
    console.print(f"\n  [bold]Scheduled:[/bold] {pending} pending task(s)")
    console.print()
