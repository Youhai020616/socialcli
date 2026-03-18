"""social accounts — list all logged-in accounts."""
from __future__ import annotations

import click
from rich.table import Table

from socialcli.auth.cookie_store import list_accounts
from socialcli.utils.output import console


@click.command()
@click.option("--platform", "-p", default="", help="Filter by platform")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def accounts(platform: str, as_json: bool):
    """List all logged-in accounts."""
    accts = list_accounts(platform)

    if not accts:
        console.print("\n  [dim]No accounts found. Login with: social login <platform>[/dim]\n")
        return

    if as_json:
        import json
        click.echo(json.dumps(accts, ensure_ascii=False, indent=2))
        return

    table = Table(title="Logged-in Accounts", show_header=True)
    table.add_column("Platform", style="cyan")
    table.add_column("Account")
    table.add_column("Nickname")
    table.add_column("Status")
    table.add_column("Login Time")

    for a in accts:
        status_style = "green" if a.get("status") == "active" else "red"
        table.add_row(
            a.get("platform", ""),
            a.get("account", ""),
            a.get("nickname", "") or "—",
            f"[{status_style}]{a.get('status', '?')}[/{status_style}]",
            a.get("login_time", "")[:19] if a.get("login_time") else "—",
        )

    console.print(table)
