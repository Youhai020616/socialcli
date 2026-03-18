"""social trending — aggregated trending from all platforms."""
from __future__ import annotations

import click
from rich.table import Table

from socialcli.utils.output import console, print_json, info


@click.command()
@click.option("--platforms", "-p", default="", help="Comma-separated platforms (default: all)")
@click.option("--count", "-n", default=10, help="Results per platform")
@click.option("--json", "as_json", is_flag=True)
@click.option("--account", "-a", default="default")
def trending(platforms, count, as_json, account):
    """Get trending topics from all platforms.

    Example: social trending -p douyin,twitter -n 10
    """
    from socialcli.platforms import registry
    registry.load_all()

    platform_list = [p.strip() for p in platforms.split(",") if p.strip()] if platforms else registry.names()
    all_results = {}

    for name in platform_list:
        platform = registry.get(name)
        if not platform:
            continue
        try:
            items = platform.trending(account)[:count]
            if items:
                all_results[name] = items
        except NotImplementedError:
            pass
        except Exception as e:
            console.print(f"  [yellow]⚠ {name}: {e}[/yellow]")

    if as_json:
        data = {k: [t.__dict__ for t in v] for k, v in all_results.items()}
        print_json(data)
        return

    if not all_results:
        info("No trending data available. Make sure you're logged in.")
        return

    for name, items in all_results.items():
        platform = registry.get(name)
        icon = platform.icon if platform else ""
        table = Table(title=f"{icon} {name} Trending")
        table.add_column("#", width=4)
        table.add_column("Topic")
        table.add_column("Hot Value")

        for item in items:
            table.add_row(str(item.rank), item.title[:50], item.hot_value)

        console.print(table)
        console.print()
