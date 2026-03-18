"""social accounts — list all logged-in accounts."""
from __future__ import annotations

import click
from rich.table import Table

from socialcli.auth.cookie_store import list_accounts
from socialcli.platforms import registry
from socialcli.utils.output import console


@click.command()
@click.option("--platform", "-p", default="", help="Filter by platform")
@click.option("--check", "-c", is_flag=True, help="Verify cookie validity")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def accounts(platform: str, check: bool, as_json: bool):
    """List all logged-in accounts.

    Use --check to verify cookies are still valid.
    """
    registry.load_all()
    accts = list_accounts(platform)

    if not accts:
        console.print("\n  [dim]No accounts found. Login with: social login <platform>[/dim]\n")
        return

    # Optionally verify each account
    if check:
        for a in accts:
            plat = registry.get(a.get("platform", ""))
            if plat:
                valid = plat.check_login(a.get("account", "default"))
                a["status"] = "active" if valid else "expired"

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
        status = a.get("status", "?")
        if status == "active":
            status_display = "[green]active[/green]"
        elif status == "expired":
            status_display = "[red]expired[/red]"
        else:
            status_display = f"[yellow]{status}[/yellow]"
        table.add_row(
            a.get("platform", ""),
            a.get("account", ""),
            a.get("nickname", "") or "—",
            status_display,
            a.get("login_time", "")[:19] if a.get("login_time") else "—",
        )

    console.print(table)
    if check:
        expired = [a for a in accts if a.get("status") == "expired"]
        if expired:
            console.print(f"\n  [yellow]⚠ {len(expired)} account(s) may have expired cookies. Run: social login <platform>[/yellow]\n")
