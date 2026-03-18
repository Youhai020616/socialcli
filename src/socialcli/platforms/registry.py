"""
Platform registry — discover and manage platform adapters.
"""
from __future__ import annotations

from typing import Dict, Optional

from socialcli.platforms.base import Platform

_platforms: Dict[str, Platform] = {}


def register(platform: Platform) -> None:
    """Register a platform adapter."""
    _platforms[platform.name] = platform


def get(name: str) -> Optional[Platform]:
    """Get a platform by name."""
    return _platforms.get(name)


def get_or_error(name: str) -> Platform:
    """Get a platform by name, raise if not found."""
    p = _platforms.get(name)
    if not p:
        available = ", ".join(sorted(_platforms.keys()))
        raise click_error(f"Unknown platform: '{name}'. Available: {available}")
    return p


def all_platforms() -> Dict[str, Platform]:
    """Get all registered platforms."""
    return dict(_platforms)


def names() -> list[str]:
    """Get sorted list of platform names."""
    return sorted(_platforms.keys())


def click_error(msg: str) -> SystemExit:
    """Helper to raise a clean error."""
    import click
    raise click.ClickException(msg)


def load_all():
    """Import all platform modules to trigger registration."""
    for mod in ("douyin", "xiaohongshu", "twitter", "reddit", "tiktok", "linkedin", "bilibili"):
        try:
            __import__(f"socialcli.platforms.{mod}")
        except ImportError:
            pass
