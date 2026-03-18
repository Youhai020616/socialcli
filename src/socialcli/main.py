"""
social — Unified social media CLI.

Usage:
    social login <platform>                 Login to a platform
    social accounts                         List logged-in accounts
    social publish "text" -p <platforms>    Publish to platforms
    social <platform> search "query"        Platform-specific search
    social <platform> publish ...           Platform-specific publish
    social <platform> trending              Platform trending
"""
from __future__ import annotations

import click

from socialcli import __version__
from socialcli.platforms import registry

BANNER = f"""
  ╔════════════════════════════════════╗
  ║   📱 socialcli v{__version__}             ║
  ║   Unified Social Media CLI         ║
  ╚════════════════════════════════════╝
"""


class SocialGroup(click.Group):
    """Custom group that delegates unknown commands to platform subgroups."""

    def get_command(self, ctx, cmd_name):
        # Ensure platforms are loaded
        registry.load_all()

        # First check built-in commands
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv

        # Check if it's a platform name → delegate to platform subgroup
        platform = registry.get(cmd_name)
        if platform and hasattr(platform, "cli_group"):
            return platform.cli_group

        return None

    def list_commands(self, ctx):
        registry.load_all()
        base = super().list_commands(ctx)
        # Add platform names
        base.extend(registry.names())
        return sorted(set(base))

    def format_help(self, ctx, formatter):
        formatter.write(BANNER)
        super().format_help(ctx, formatter)


@click.group(cls=SocialGroup, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="socialcli")
@click.pass_context
def cli(ctx):
    """📱 Unified social media CLI — publish, search, trending across all platforms."""
    # Load all platform adapters
    registry.load_all()

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register built-in commands
from socialcli.commands.login import login
from socialcli.commands.accounts import accounts
from socialcli.commands.publish import publish
from socialcli.commands.schedule import schedule
from socialcli.commands.ai import ai
from socialcli.commands.batch import batch
from socialcli.commands.monitor import monitor
from socialcli.commands.trending import trending

cli.add_command(login)
cli.add_command(accounts)
cli.add_command(publish)
cli.add_command(schedule)
cli.add_command(ai)
cli.add_command(batch)
cli.add_command(monitor)
cli.add_command(trending)
