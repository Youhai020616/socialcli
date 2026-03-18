"""social monitor — monitor platforms for keywords."""
from __future__ import annotations

import click
from socialcli.utils import output


@click.command()
@click.option("--keywords", "-k", required=True, help="Comma-separated keywords to monitor")
@click.option("--platforms", "-p", default="", help="Comma-separated platforms (default: all)")
@click.option("--interval", "-i", default=60, help="Check interval in seconds")
@click.option("--count", "-n", default=0, help="Max checks (0 = infinite)")
@click.option("--account", "-a", default="default")
def monitor(keywords, platforms, interval, count, account):
    """Monitor platforms for keyword mentions.

    Examples:

        social monitor -k "my product,competitor" -p reddit,twitter

        social monitor -k "AI tools" -p all -i 120

        social monitor -k "brand name" -p reddit -n 10
    """
    from socialcli.platforms import registry
    from socialcli.core.monitor import monitor_keywords

    registry.load_all()

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()] if platforms else registry.names()

    if not keyword_list:
        output.error("No keywords specified")
        raise SystemExit(1)

    monitor_keywords(
        keywords=keyword_list,
        platforms=platform_list,
        interval=interval,
        max_checks=count,
        account=account,
    )
