"""social logout — remove saved credentials."""
from __future__ import annotations

import click

from socialcli.auth.cookie_store import delete_account, list_accounts
from socialcli.utils import output


@click.command()
@click.argument("platform")
@click.option("--account", "-a", default="default", help="Account name")
def logout(platform, account):
    """Logout from a platform (delete saved cookies).

    Examples:

        social logout reddit

        social logout twitter -a work
    """
    if delete_account(platform, account):
        output.success(f"Logged out from {platform} (account: {account})")
    else:
        output.error(f"No saved session for {platform}/{account}")
