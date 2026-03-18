"""
Multi-platform publisher — publish content to multiple platforms at once.
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _publish_one(
    platform_name: str,
    content: Content,
    account: str,
) -> PublishResult:
    """Publish to a single platform (called from thread pool)."""
    platform = registry.get(platform_name)
    if not platform:
        return PublishResult(success=False, platform=platform_name, error=f"Unknown platform: {platform_name}")

    if not platform.check_login(account):
        return PublishResult(success=False, platform=platform_name, error=f"Not logged in. Run: social login {platform_name}")

    # Cookie age warning
    age = platform.cookie_age_days(account)
    if age is not None and age >= 7:
        console.print(f"  [yellow]⚠ {platform_name}: cookies are {age}d old, consider: social login {platform_name}[/yellow]")

    adapted = content_adapter.adapt(content, platform_name)
    try:
        result = platform.publish(adapted, account)
        _save_history(result, adapted)
        # If publish failed, add helpful hint
        if not result.success:
            result.error = _friendly_error(result.error, platform_name)
        return result
    except Exception as e:
        logger.debug("publish error %s: %s", platform_name, e)
        return PublishResult(success=False, platform=platform_name, error=_friendly_error(str(e), platform_name))


def publish_all(
    content: Content,
    platforms: List[str],
    account: str = "default",
    dry_run: bool = False,
) -> List[PublishResult]:
    """
    Publish content to multiple platforms.

    Uses parallel execution for real publishes (ThreadPoolExecutor).
    Dry-run is always sequential (no network calls).
    """
    results = []

    # Show warnings for all platforms first
    for platform_name in platforms:
        warnings = content_adapter.validate(content, platform_name)
        for w in warnings:
            console.print(f"  [yellow]⚠ {platform_name}: {w}[/yellow]")

    if dry_run:
        for platform_name in platforms:
            adapted = content_adapter.adapt(content, platform_name)
            results.append(PublishResult(
                success=True,
                platform=platform_name,
                post_id="",
                url="",
                error=f"[DRY RUN] title={adapted.title[:30]!r} text={adapted.text[:50]!r}",
            ))
        return results

    # Real publish — parallel execution
    if len(platforms) == 1:
        # Single platform, no need for thread pool
        console.print(f"  [dim]Publishing to {platforms[0]}...[/dim]")
        return [_publish_one(platforms[0], content, account)]

    console.print(f"  [dim]Publishing to {len(platforms)} platforms in parallel...[/dim]")
    start = time.monotonic()

    with ThreadPoolExecutor(max_workers=min(len(platforms), 5)) as pool:
        futures = {
            pool.submit(_publish_one, name, content, account): name
            for name in platforms
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                results.append(result)
                status = "✔" if result.success else "✖"
                logger.debug("%s %s: %s", status, name, result.url or result.error)
            except Exception as e:
                results.append(PublishResult(success=False, platform=name, error=str(e)))

    elapsed = time.monotonic() - start
    logger.debug("Parallel publish completed in %.1fs", elapsed)

    # Sort results to match input order
    order = {name: i for i, name in enumerate(platforms)}
    results.sort(key=lambda r: order.get(r.platform, 999))

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


_ERROR_HINTS = {
    "USER_REQUIRED": "Cookie expired. Run: social login {platform}",
    "RATELIMIT": "Rate limited. Wait a few minutes and try again.",
    "403": "Access denied — cookie may have expired. Run: social login {platform}",
    "401": "Unauthorized — cookie expired. Run: social login {platform}",
    "Cookie expired": "Run: social login {platform}",
    "Connection refused": "Network error. Check your internet connection.",
    "timed out": "Request timed out. Try again later.",
    "timeout": "Request timed out. Try again later.",
}


def _friendly_error(error: str, platform_name: str) -> str:
    """Map known error patterns to user-friendly messages."""
    if not error:
        return error
    for pattern, hint in _ERROR_HINTS.items():
        if pattern.lower() in error.lower():
            return hint.format(platform=platform_name)
    return error


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
