# socialcli

Unified social media CLI — publish, search, trending, monitor across 7 platforms from one command line.

IMPORTANT: Each platform uses reverse-engineered APIs + Playwright browser automation. These APIs are undocumented and may break at any time. Always read the actual platform client code before modifying.

## Project Structure

```
src/socialcli/
  main.py                — CLI entry (Click), SocialGroup auto-delegates to platform subgroups
  __init__.py             — Version string
  auth/
    browser_login.py      — Playwright browser login (QR scan → capture cookies)
    cookie_store.py       — Cookie persistence (~/.socialcli/accounts/<platform>/<account>.json)
  core/
    ai_writer.py          — AI content generation (OpenAI-compatible API)
    content_adapter.py    — Adapt Content to platform-specific format (char limits, tags, etc.)
    publisher.py          — Multi-platform publish orchestration
    scheduler.py          — Scheduled posts (~/.socialcli/schedule.json)
    batch.py              — Batch operations
    monitor.py            — Keyword monitoring loop across platforms
  platforms/
    base.py               — Platform ABC + data models (Content, PublishResult, SearchResult, etc.)
    registry.py           — Platform discovery and registration
    douyin/               — 抖音 (client.py + browser.py)
    xiaohongshu/          — 小红书 (client.py + browser.py)
    twitter/              — Twitter/X (client.py)
    reddit/               — Reddit (client.py)
    tiktok/               — TikTok (client.py + browser.py)
    linkedin/             — LinkedIn (client.py + browser.py)
    bilibili/             — B站 (client.py + browser.py)
  commands/               — Click commands (login, accounts, publish, schedule, ai, batch, monitor, trending)
  utils/
    output.py             — Rich-based output (print_json, print_table, success/error/warn)
```

## Core Abstractions

### Platform Interface (`platforms/base.py`)

All platforms implement `Platform` ABC. DO NOT change the interface without updating all 7 adapters.

```python
class Platform(ABC):
    name: str              # e.g. "douyin"
    display_name: str      # e.g. "抖音"
    icon: str              # e.g. "🎬"

    # Required
    def login(account="default", **kwargs) -> bool
    def check_login(account="default") -> bool
    def publish(content: Content, account="default") -> PublishResult
    def search(query, account="default", **kwargs) -> List[SearchResult]

    # Optional
    def trending(...) -> List[TrendingItem]
    def like / comment / follow / download / analytics / me
```

### Data Models (`platforms/base.py`)

All are `@dataclass`. Do NOT convert to Pydantic or dict — keep as dataclasses.

- `Content` — unified publish payload (title, text, images, video, link, tags, extras)
- `PublishResult` — success/failure + url/error
- `SearchResult` — title, url, author, likes, comments, snippet
- `TrendingItem` — rank, title, url, hot_value
- `AccountInfo` — platform, account, nickname, is_logged_in

### Content Adapter (`core/content_adapter.py`)

`PLATFORM_RULES` dict defines per-platform constraints (max_text, tag format, merge_title_to_text, etc.). When adding a new platform, add its rules here.

## Platform Architecture Pattern

Every platform follows the same structure:

```
platforms/<name>/
  __init__.py      — Instantiate + register with registry
  client.py        — Platform class (login, search, trending, publish, CLI subgroup)
  browser.py       — Playwright automation for publish (only platforms needing browser upload)
```

### Registration Pattern

```python
# platforms/douyin/__init__.py
from socialcli.platforms.douyin.client import DouyinPlatform
from socialcli.platforms import registry

_platform = DouyinPlatform()
registry.register(_platform)
```

### CLI Subgroup Pattern

Each platform client exposes a `cli_group` property returning a Click group. `SocialGroup` in main.py auto-delegates unknown commands to platform subgroups:

```
social douyin search "美食"     →  DouyinPlatform.cli_group → search command
social douyin trending          →  DouyinPlatform.cli_group → trending command
```

## Authentication

- Login: Playwright opens real browser → user scans QR / enters credentials → cookies captured
- Storage: `~/.socialcli/accounts/<platform>/<account>.json`
- Multi-account: `--account` / `-a` flag on all commands
- Cookie format: list of `{name, value, domain, path, expires, httpOnly, secure, sameSite}`
- `cookie_string()` converts to HTTP header format: `"name1=val1; name2=val2"`

## AI Integration (`core/ai_writer.py`)

Uses OpenAI-compatible API (works with OpenAI, Claude proxy, DeepSeek, etc.)

Config priority:
1. `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `AI_MODEL` env vars
2. `~/.socialcli/config.json` → `ai_api_key`, `ai_base_url`, `ai_model`

HTTP client: `httpx` (NOT `openai` SDK). Do NOT add `openai` as a required dependency.

## Coding Conventions

- Python >= 3.10, use `from __future__ import annotations`
- CLI framework: Click. Do NOT switch to typer/argparse
- HTTP client: `httpx`. Do NOT use `requests`
- Output: `rich` for tables/colors. stdout = data (JSON), stderr = status messages
- Async: Only `browser_login.py` uses async (Playwright). Everything else is sync
- All commands go in `src/socialcli/commands/<name>.py`, register in `main.py`
- Type hints on all function signatures
- Dataclasses for data models, not Pydantic/TypedDict/NamedTuple

## Adding a New Platform

1. Create `src/socialcli/platforms/<name>/`
2. Implement `client.py` with class extending `Platform`
3. Add `__init__.py` that instantiates + registers
4. Add platform rules to `core/content_adapter.py` `PLATFORM_RULES`
5. Add module name to `registry.load_all()` list
6. Add `cli_group` property with Click subcommands

## Data Storage

```
~/.socialcli/
  accounts/<platform>/<account>.json    — Cookies + account info
  config.json                           — AI config, preferences
  schedule.json                         — Scheduled publish tasks
```

## Commands

```bash
pip install -e .                        # Install in dev mode
pip install -e ".[ai]"                  # With AI support
pip install -e ".[dev]"                 # With test deps
playwright install chromium             # Required for login + browser publish
pytest                                  # Run tests
social --help                           # CLI help
```
