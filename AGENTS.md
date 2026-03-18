# SocialCLI

Unified social media CLI — publish, search, trending, monitor across 13 platforms from one command line.

**Status: v0.1.0 Alpha — early prototype, core API paths NOT yet validated end-to-end.**

> IMPORTANT: Each platform uses reverse-engineered APIs + Playwright browser automation.
> These APIs are undocumented and may break at any time. Always read the actual platform
> client code before modifying. Many API endpoints contain hardcoded tokens/queryIds that
> will need dynamic resolution before production use.

---

## Project Structure

```
src/socialcli/
  main.py                — CLI entry (Click), SocialGroup auto-delegates to platform subgroups
  __init__.py            — Version string ("0.1.0")

  auth/
    browser_login.py     — Playwright browser login (QR scan / password → capture cookies)
    cookie_store.py      — Cookie persistence (~/.socialcli/accounts/<platform>/<account>.json)

  core/
    publisher.py         — Multi-platform publish orchestration (sync, sequential)
    content_adapter.py   — Adapt Content to platform-specific format (char limits, tags, etc.)
    scheduler.py         — Scheduled posts (~/.socialcli/schedule.json)
    batch.py             — Batch publish from CSV/JSON/directory
    monitor.py           — Keyword monitoring loop across platforms
    ai_writer.py         — AI content generation (OpenAI-compatible API via httpx)

  platforms/
    base.py              — Platform ABC + data models (Content, PublishResult, SearchResult, etc.)
    registry.py          — Platform discovery and registration (loads all 13 platform modules)

    # ── Phase 1: Core 7 (have client.py + some browser.py) ──
    douyin/              — 抖音 (client.py + browser.py)
    xiaohongshu/         — 小红书 (client.py + browser.py)
    twitter/             — Twitter/X (client.py only, no browser.py)
    reddit/              — Reddit (client.py only, no browser.py)
    tiktok/              — TikTok (client.py + browser.py)
    linkedin/            — LinkedIn (client.py + browser.py)
    bilibili/            — B站 (client.py + browser.py)

    # ── Phase 2: Extended 6 (skeleton stubs, minimal implementation) ──
    weibo/               — 微博 (client.py + browser.py)
    kuaishou/            — 快手 (client.py + browser.py)
    youtube/             — YouTube (client.py + browser.py)
    facebook/            — Facebook (client.py + browser.py)
    instagram/           — Instagram (client.py + browser.py)
    threads/             — Threads (client.py + browser.py)

  commands/              — Click commands (login, accounts, publish, schedule, ai, batch, monitor, trending)
  utils/
    output.py            — Rich-based output (print_json, print_table, success/error/warn)

github/                  — Reference projects (rdt-cli, etc.), NOT imported by src code
plan/
  socialcli-plan.md      — Product spec, architecture design, roadmap
tests/                   — EMPTY — no tests exist yet
```

---

## Core Abstractions

### Platform Interface (`platforms/base.py`)

All platforms implement `Platform` ABC. DO NOT change the interface without updating all 13 adapters.

```python
class Platform(ABC):
    name: str              # e.g. "douyin"
    display_name: str      # e.g. "抖音"
    icon: str              # e.g. "🎬"

    # Required (abstract)
    def login(account="default", **kwargs) -> bool
    def check_login(account="default") -> bool
    def publish(content: Content, account="default") -> PublishResult
    def search(query, account="default", **kwargs) -> List[SearchResult]

    # Optional (default raises NotImplementedError)
    def trending(...) -> List[TrendingItem]
    def like / comment / follow / download / analytics / me
```

### Data Models (`platforms/base.py`)

All are `@dataclass`. Do NOT convert to Pydantic or dict — keep as dataclasses.

- `Content` — unified publish payload (title, text, images, video, link, tags, visibility, schedule_time, extras)
- `PublishResult` — success/failure + platform + post_id + url/error
- `SearchResult` — title, url, author, likes, comments, snippet, thumbnail, created_at
- `TrendingItem` — rank, title, url, hot_value, category
- `AccountInfo` — platform, account, nickname, user_id, is_logged_in

### Content Adapter (`core/content_adapter.py`)

`PLATFORM_RULES` dict defines per-platform constraints (max_text, tag format, merge_title_to_text, media type, etc.). When adding a new platform, add its rules here. Currently only defines rules for the core 7 platforms.

### Platform Registry (`platforms/registry.py`)

`load_all()` imports all 13 platform modules. Each module's `__init__.py` instantiates and registers. `SocialGroup.get_command()` calls `load_all()` on every CLI invocation.

---

## Platform Architecture Pattern

Every platform follows the same structure:

```
platforms/<name>/
  __init__.py      — Instantiate + register with registry
  client.py        — Platform class (login, search, trending, publish, cli_group property)
  browser.py       — Playwright automation for publish (optional, only for browser-based upload)
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
social reddit trending          →  RedditPlatform.cli_group → trending command
```

---

## Authentication

- Login: Playwright opens real browser → user scans QR / enters credentials → cookies captured
- Storage: `~/.socialcli/accounts/<platform>/<account>.json` (plain JSON, NOT encrypted)
- Multi-account: `--account` / `-a` flag on all commands
- Cookie format: list of `{name, value, domain, path, expires, httpOnly, secure, sameSite}`
- `cookie_string()` converts to HTTP header format: `"name1=val1; name2=val2"`

---

## AI Integration (`core/ai_writer.py`)

Uses OpenAI-compatible chat completions API via raw `httpx` calls (NOT the `openai` SDK).

Config priority:
1. `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `AI_MODEL` env vars
2. `~/.socialcli/config.json` → `ai_api_key`, `ai_base_url`, `ai_model`

Functions: `generate(topic, platforms)`, `adapt(text, target_platform)`, `suggest_tags(text, platform)`

---

## Known Technical Debt & Issues

### Critical — Must Fix Before Any Release

1. **Zero test coverage**: `tests/` directory is empty. No unit tests, no integration tests, no mocks.
   Priority: Add tests for `content_adapter`, `cookie_store`, `scheduler`, `batch` first (pure logic, no network).

2. **Silent error swallowing**: Almost every API call wraps in `except Exception: return []`.
   Users cannot distinguish "no results" from "request failed / cookie expired / anti-bot blocked".
   Fix: Add structured logging, return error info, or raise typed exceptions.

3. **Cookie stored in plaintext**: `~/.socialcli/accounts/` contains full session cookies as unencrypted JSON.
   Plan doc mentions encryption but it is NOT implemented. Consider `keyring` or at minimum file permission enforcement.

4. **Hardcoded API tokens that will break**:
   - `twitter/client.py`: Bearer token and `queryId` (`znCbgGaBcIFDlGEhXdFVzg`) are hardcoded. Twitter rotates queryIds with frontend deploys.
   - `douyin/client.py`: Missing `a_bogus`, `msToken` anti-crawl signature params — search API calls will likely be blocked.
   - `linkedin/client.py`: Voyager API GraphQL endpoint and response parsing are speculative / unverified.

### High — Code Quality

5. **Massive code duplication across platform clients**:
   - `_get_headers()` repeated in every client with same pattern
   - `me()` method is near-identical in all 13 clients
   - `cli_group` search/trending/publish command boilerplate repeated everywhere
   Fix: Extract common methods to `Platform` base class or a mixin.

6. **Sync-only, sequential publishing**: `publisher.py` publishes to platforms in a for-loop.
   Publishing to 7+ platforms is linearly slow. Plan doc says "并行发布引擎" but actual code is serial.
   Consider `asyncio.gather` or `concurrent.futures.ThreadPoolExecutor`.

7. **`github/` directory not integrated**: Contains full `rdt-cli` project with tests, fingerprint, session management.
   Reddit client does NOT import from it. Either integrate or remove to reduce confusion.

### Medium — Functionality Gaps

8. **Scheduler has no daemon**: `scheduler.py` requires manual `social schedule run`. No cron integration,
   no background process, no systemd service. User must set up external cron.

9. **Monitor is naive polling**: `monitor.py` uses `time.sleep()` loop with no dedup persistence
   (in-memory `seen_urls` set lost on restart). No webhook/notification support.

10. **Phase 2 platforms are stubs**: The 6 extended platforms (weibo, kuaishou, youtube, facebook, instagram, threads)
    exist as registered modules but are minimally implemented. Most browser.py files are <60 lines of skeleton code.

11. **Content adapter only covers core 7**: `PLATFORM_RULES` dict does not have entries for the 6 extended platforms.
    `adapt()` falls back to empty dict, meaning no content transformation for those platforms.

12. **`import re` inside function body**: `bilibili/client.py` imports `re` inside `search()` on every call.
    Move to module-level import.

---

## Development Priorities (Recommended Order)

### P0 — Validate Core Path
- [ ] Pick 2 stable platforms (Reddit + Bilibili — public JSON APIs), run end-to-end: login → search → publish
- [ ] Fix error handling: replace `except Exception: return []` with logging + typed errors
- [ ] Add basic tests for pure-logic modules: `content_adapter`, `cookie_store`, `scheduler`, `batch`

### P1 — Harden Existing Platforms
- [ ] Twitter: implement dynamic queryId resolution (scrape from main.js bundle)
- [ ] Douyin: add anti-crawl signature generation (`a_bogus`, `msToken`)
- [ ] Extract common base class methods (`_get_headers`, `me`, CLI boilerplate)
- [ ] Add integration test fixtures (mock HTTP responses per platform)

### P2 — Security & Reliability
- [ ] Encrypt cookie storage (or use system keyring)
- [ ] Add retry logic with exponential backoff for API calls
- [ ] Add cookie expiry detection and auto-prompt for re-login
- [ ] Add `--verbose` / `--debug` flag for detailed logging

### P3 — Feature Completion
- [ ] Async parallel publishing in `publisher.py`
- [ ] Scheduler daemon mode or cron helper
- [ ] Complete Phase 2 platform implementations
- [ ] Add `content_adapter` rules for extended platforms

---

## Coding Conventions

- Python >= 3.10, use `from __future__ import annotations` in every file
- CLI framework: **Click**. Do NOT switch to typer/argparse
- HTTP client: **httpx** (sync). Do NOT use `requests` or `aiohttp`
- Output: **rich** for tables/colors. stdout = data (JSON), stderr = status messages
- Async: Only `browser_login.py` and `browser.py` files use async (Playwright). All other code is sync
- All commands go in `src/socialcli/commands/<name>.py`, register in `main.py`
- Type hints on all function signatures
- Dataclasses for data models, NOT Pydantic/TypedDict/NamedTuple
- Imports at module level (avoid in-function imports except for optional deps like `playwright`)
- `from __future__ import annotations` must be the first import in every file

### Error Handling Convention (TO BE ADOPTED)
```python
# BAD — current pattern (do not continue this)
try:
    resp = httpx.get(...)
except Exception:
    return []

# GOOD — target pattern
import logging
logger = logging.getLogger(__name__)

try:
    resp = httpx.get(...)
    resp.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.warning("API error %s: %s", e.response.status_code, e.response.text[:200])
    return []
except httpx.RequestError as e:
    logger.error("Request failed: %s", e)
    return []
```

---

## Adding a New Platform

1. Create `src/socialcli/platforms/<name>/`
2. Implement `client.py` with class extending `Platform`
3. Add `__init__.py` that instantiates + registers
4. Add platform rules to `core/content_adapter.py` → `PLATFORM_RULES`
5. Add module name to `registry.load_all()` list
6. Add `cli_group` property with Click subcommands (search, trending, publish)
7. Add browser.py if platform requires Playwright for upload
8. Write at least mock-based tests for search response parsing

---

## Data Storage

```
~/.socialcli/
  accounts/<platform>/<account>.json    — Cookies + account info (PLAINTEXT)
  config.json                           — AI config, default_platforms, preferences
  schedule.json                         — Scheduled publish tasks
```

---

## Dev Commands

```bash
pip install -e .                        # Install in dev mode
pip install -e ".[ai]"                  # With AI support (openai)
pip install -e ".[dev]"                 # With test deps (pytest, pytest-asyncio)
playwright install chromium             # Required for login + browser publish

pytest                                  # Run tests (currently empty)
social --help                           # CLI help
social --version                        # Show version

# Quick smoke test
social accounts                         # Should list (empty if no logins)
social trending -p bilibili --json      # Bilibili trending (no login needed for public API)
```

---

## Reference Materials

- `plan/socialcli-plan.md` — Full product spec, architecture, roadmap, commercial strategy
- `github/rdt-cli/` — Reference Reddit CLI project (NOT imported, for API research only)
- Platform APIs are reverse-engineered; study browser Network tab for each platform before modifying
