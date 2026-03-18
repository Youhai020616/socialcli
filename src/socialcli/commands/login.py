"""social login <platform> — login to a platform."""
from __future__ import annotations

import click

from socialcli.platforms import registry
from socialcli.utils import output


@click.command()
@click.argument("platform")
@click.option("--account", "-a", default="default", help="Account name (for multi-account)")
@click.option("--headless", is_flag=True, default=False, help="Headless browser (not recommended for login)")
def login(platform: str, account: str, headless: bool):
    """Login to a social media platform."""
    p = registry.get(platform)
    if not p:
        output.error(f"Unknown platform: '{platform}'")
        output.dim(f"  Available: {', '.join(registry.names())}")
        raise SystemExit(1)

    output.info(f"Logging in to {p.display_name}...")
    success = p.login(account=account, headless=headless)

    if success:
        output.success(f"Logged in to {p.display_name} (account: {account})")
    else:
        output.error(f"Login failed for {p.display_name}")
        raise SystemExit(1)
