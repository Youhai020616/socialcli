"""social config — view and set configuration."""
from __future__ import annotations

import json
from pathlib import Path

import click

from socialcli.utils import output

CONFIG_FILE = Path.home() / ".socialcli" / "config.json"


def _load() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


@click.group()
def config():
    """View and set configuration."""
    pass


@config.command("show")
def show():
    """Show all configuration."""
    data = _load()
    if not data:
        output.info(f"No configuration set. Config file: {CONFIG_FILE}")
        return
    output.info(f"Config: {CONFIG_FILE}")
    # Mask sensitive values
    for k, v in sorted(data.items()):
        if "key" in k.lower() or "token" in k.lower() or "secret" in k.lower():
            display = str(v)[:8] + "..." if v else "(empty)"
        else:
            display = str(v)
        click.echo(f"  {k} = {display}")


@config.command("set")
@click.argument("key")
@click.argument("value")
def set_value(key, value):
    """Set a configuration value.

    Examples:

        social config set ai_api_key sk-xxx

        social config set ai_model gpt-4o-mini

        social config set default_platforms reddit,bilibili
    """
    data = _load()
    data[key] = value
    _save(data)
    output.success(f"{key} = {value[:20]}{'...' if len(value) > 20 else ''}")


@config.command("get")
@click.argument("key")
def get_value(key):
    """Get a configuration value."""
    data = _load()
    value = data.get(key)
    if value is None:
        output.error(f"Key '{key}' not set")
        raise SystemExit(1)
    click.echo(value)


@config.command("unset")
@click.argument("key")
def unset_value(key):
    """Remove a configuration value."""
    data = _load()
    if key in data:
        del data[key]
        _save(data)
        output.success(f"Removed '{key}'")
    else:
        output.error(f"Key '{key}' not set")
