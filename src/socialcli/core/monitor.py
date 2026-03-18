"""
Monitor — watch platforms for keyword mentions, trending changes, etc.
"""
from __future__ import annotations

import time
import random
import json
from datetime import datetime, timezone
from typing import List

from socialcli.platforms import registry
from socialcli.platforms.base import SearchResult


def monitor_keywords(
    keywords: List[str],
    platforms: List[str],
    interval: int = 60,
    max_checks: int = 0,
    account: str = "default",
    callback=None,
) -> None:
    """
    Monitor platforms for keyword mentions.

    Args:
        keywords: Keywords to search for
        platforms: Platform names to monitor
        interval: Check interval in seconds
        max_checks: Max number of checks (0 = infinite)
        account: Account name
        callback: Called with (platform, keyword, results) on each check
    """
    from rich.console import Console
    console = Console(stderr=True)

    seen_urls = set()
    check_count = 0
    new_total = 0

    console.print(f"\n[bold]📡 Monitoring {len(keywords)} keyword(s) on {len(platforms)} platform(s)[/bold]")
    console.print(f"[dim]  Keywords: {', '.join(keywords)}[/dim]")
    console.print(f"[dim]  Platforms: {', '.join(platforms)}[/dim]")
    console.print(f"[dim]  Interval: {interval}s | Ctrl+C to stop[/dim]\n")

    registry.load_all()

    try:
        while True:
            check_count += 1
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

            for platform_name in platforms:
                platform = registry.get(platform_name)
                if not platform:
                    continue

                for keyword in keywords:
                    try:
                        results = platform.search(keyword, account, count=10)

                        new_results = []
                        for r in results:
                            if r.url and r.url not in seen_urls:
                                seen_urls.add(r.url)
                                new_results.append(r)

                        if new_results:
                            new_total += len(new_results)
                            console.print(
                                f"[green]✔ [{ts}] {platform_name}: {len(new_results)} new for \"{keyword}\"[/green]"
                            )
                            for r in new_results[:3]:
                                console.print(f"  [cyan]{r.title[:60]}[/cyan]")
                                console.print(f"  [dim]{r.url}[/dim]")

                            if callback:
                                callback(platform_name, keyword, new_results)
                        else:
                            console.print(
                                f"[dim][{ts}] {platform_name}: no new results for \"{keyword}\"[/dim]",
                                end="\r",
                            )
                    except Exception as e:
                        console.print(f"[yellow]⚠ [{ts}] {platform_name}/{keyword}: {e}[/yellow]")

                    # Small delay between searches
                    time.sleep(random.uniform(1, 3))

            if 0 < max_checks <= check_count:
                break

            # Wait for next check with jitter
            jitter = interval + random.uniform(-interval * 0.1, interval * 0.1)
            time.sleep(max(jitter, 5))

    except KeyboardInterrupt:
        pass

    console.print(f"\n[bold]Monitoring stopped: {check_count} checks, {new_total} new items found[/bold]\n")
