"""
Multi-platform publisher — publish content to multiple platforms at once.
"""
from __future__ import annotations

from typing import List

from rich.console import Console
from rich.table import Table

from socialcli.platforms.base import Content, PublishResult
from socialcli.platforms import registry
from socialcli.core import content_adapter

console = Console(stderr=True)


def publish_all(
    content: Content,
    platforms: List[str],
    account: str = "default",
    dry_run: bool = False,
) -> List[PublishResult]:
    """
    Publish content to multiple platforms.

    Automatically adapts content format for each platform.
    """
    results = []

    for platform_name in platforms:
        platform = registry.get(platform_name)
        if not platform:
            results.append(PublishResult(
                success=False,
                platform=platform_name,
                error=f"Unknown platform: {platform_name}",
            ))
            continue

        # Check login
        if not platform.check_login(account):
            results.append(PublishResult(
                success=False,
                platform=platform_name,
                error=f"Not logged in. Run: social login {platform_name}",
            ))
            continue

        # Validate content
        warnings = content_adapter.validate(content, platform_name)
        for w in warnings:
            console.print(f"  [yellow]⚠ {platform_name}: {w}[/yellow]")

        # Adapt content
        adapted = content_adapter.adapt(content, platform_name)

        if dry_run:
            results.append(PublishResult(
                success=True,
                platform=platform_name,
                error=f"[DRY RUN] title={adapted.title[:30]!r} text={adapted.text[:50]!r}",
            ))
            continue

        # Publish
        try:
            console.print(f"  [dim]Publishing to {platform.display_name}...[/dim]")
            result = platform.publish(adapted, account)
            results.append(result)
        except Exception as e:
            results.append(PublishResult(
                success=False,
                platform=platform_name,
                error=str(e),
            ))

    return results


def print_results(results: List[PublishResult]) -> None:
    """Pretty-print publish results."""
    table = Table(title="Publish Results", show_header=True)
    table.add_column("Platform", style="cyan")
    table.add_column("Status")
    table.add_column("URL / Error")

    for r in results:
        status = "[green]✔ Success[/green]" if r.success else "[red]✖ Failed[/red]"
        detail = r.url if r.success and r.url else r.error
        table.add_row(r.platform, status, detail or "—")

    console.print(table)

    success = sum(1 for r in results if r.success)
    total = len(results)
    console.print(f"\n  [bold]{success}/{total} platforms published successfully.[/bold]\n")
