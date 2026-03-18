"""
Multi-platform publisher — publish content to multiple platforms at once.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table

from socialcli.platforms.base import Content, PublishResult
from socialcli.platforms import registry
from socialcli.core import content_adapter

console = Console(stderr=True)
logger = logging.getLogger(__name__)

HISTORY_FILE = Path.home() / ".socialcli" / "history.jsonl"


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
                post_id="",
                url="",
                error=f"[DRY RUN] title={adapted.title[:30]!r} text={adapted.text[:50]!r}",
            ))
            continue

        # Check login (only for real publish, not dry-run)
        if not platform.check_login(account):
            results.append(PublishResult(
                success=False,
                platform=platform_name,
                error=f"Not logged in. Run: social login {platform_name}",
            ))
            continue

        # Publish
        try:
            console.print(f"  [dim]Publishing to {platform.display_name}...[/dim]")
            result = platform.publish(adapted, account)
            results.append(result)
            _save_history(result, adapted)
        except Exception as e:
            logger.debug("publish error %s: %s", platform_name, e)
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
    table.add_column("Detail")

    for r in results:
        if r.success and r.error and r.error.startswith("[DRY RUN]"):
            status = "[blue]⊘ Dry Run[/blue]"
            detail = r.error
        elif r.success:
            status = "[green]✔ Success[/green]"
            detail = r.url or "—"
        else:
            status = "[red]✖ Failed[/red]"
            detail = r.error or "Unknown error"
        table.add_row(r.platform, status, detail)

    console.print(table)

    success = sum(1 for r in results if r.success)
    total = len(results)
    console.print(f"\n  [bold]{success}/{total} platforms published successfully.[/bold]\n")


def _save_history(result: PublishResult, content: Content) -> None:
    """Append publish result to history file (JSONL)."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "time": datetime.now(timezone.utc).isoformat(),
            "platform": result.platform,
            "success": result.success,
            "post_id": result.post_id,
            "url": result.url,
            "error": result.error,
            "title": content.title[:100],
            "text": content.text[:200],
        }
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("Failed to save history: %s", exc)
