# SocialCLI

Unified social media CLI — publish, search, trending, monitor across 13 platforms from one command line.

**Status: v0.1.0 Alpha — Reddit + Twitter fully working (login → search → trending → publish verified). Bilibili search/trending working. 106 tests passing.**

> IMPORTANT: Each platform uses reverse-engineered APIs + browser cookie extraction.
> These APIs are undocumented and may break at any time. Always read the actual platform
> client code before modifying.

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

**Primary method**: `browser-cookie3` extracts cookies from local Chrome/Firefox/Edge/Brave.
Configured per-platform via `cookie_domain` and `required_cookies` class attributes on `Platform`.

**Fallback**: Playwright opens real browser → user scans QR / enters credentials → cookies captured.

- `login_with_browser_cookies()` — base class method, tries browser extraction first
- Storage: `~/.socialcli/accounts/<platform>/<account>.json` (plain JSON)
- Multi-account: `--account` / `-a` flag on all commands
- `cookie_string()` converts to HTTP header format: `"name1=val1; name2=val2"`

Platform auth requirements:
- Reddit: `reddit_session` cookie + modhash CSRF
- Twitter: `auth_token` + `ct0` cookies + bearer token + x-client-transaction-id
- Bilibili: `SESSDATA` + `bili_jct` cookies
- 小红书: `a1` + `web_session` cookies + xhshow API signing
- LinkedIn: `li_at` + `JSESSIONID` cookies

---

## AI Integration (`core/ai_writer.py`)

Uses OpenAI-compatible chat completions API via raw `httpx` calls (NOT the `openai` SDK).

Config priority:
1. `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `AI_MODEL` env vars
2. `~/.socialcli/config.json` → `ai_api_key`, `ai_base_url`, `ai_model`

Functions: `generate(topic, platforms)`, `adapt(text, target_platform)`, `suggest_tags(text, platform)`

---

## Known Technical Debt & Issues

### Resolved ✅

- ~~Zero test coverage~~ → **106 tests passing** (10 test files)
- ~~Silent error swallowing~~ → Reddit + Bilibili use `logger.debug()`, `--verbose` flag added
- ~~Hardcoded Twitter queryIds~~ → 4-tier dynamic resolution (JS scan → GitHub → fallback)
- ~~Code duplication~~ → `_get_headers()`, `me()`, `login_with_browser_cookies()` in base class
- ~~`_platform` scope bug~~ → All 13 platforms use `platform = self` closure capture

### Remaining — High Priority

1. **Cookie stored in plaintext**: `~/.socialcli/accounts/` contains session cookies as unencrypted JSON.
   Consider `keyring` or file permission enforcement.

2. **Sync-only sequential publishing**: `publisher.py` publishes in a for-loop.
   Publishing to many platforms is linearly slow. Consider `concurrent.futures.ThreadPoolExecutor`.

3. **Douyin/TikTok API signatures**: Missing `a_bogus`, `msToken` anti-crawl params.
   Search/trending APIs return empty without proper signing.

4. **小红书 search returns empty**: xhshow signing integrated, API returns 200 + code 0,
   but 0 results. Likely needs session prewarm or additional cookie state.

### Remaining — Medium Priority

5. **Scheduler has no daemon**: Requires manual `social schedule run`. User needs external cron.

6. **LinkedIn Voyager API**: Auth verified (me() works), but search endpoint returns 400/404.
   API format has changed, needs research.

7. **Phase 2 platforms are stubs**: weibo/kuaishou/youtube/facebook/instagram/threads
   have minimal client code. Not a priority.

---

## Development Priorities (Updated)

### P0 — Done ✅
- [x] Reddit + Bilibili end-to-end validated
- [x] Twitter search + trending + publish working
- [x] 106 tests, error logging, `--verbose`, base class extraction
- [x] browser-cookie3 instant login for 5 platforms
- [x] Cross-platform publish verified (Reddit + Twitter simultaneously)

### P1 — Next
- [ ] Bilibili publish: verify Playwright video upload flow
- [ ] 小红书 search: debug session prewarm (API signed correctly, returns 0 results)
- [ ] Parallel publishing with `concurrent.futures.ThreadPoolExecutor`
- [ ] Cookie expiry detection + auto re-login prompt

### P2 — Later
- [ ] Douyin/TikTok: anti-crawl signature (`a_bogus`, `msToken`)
- [ ] LinkedIn: research new Voyager API search format
- [ ] Encrypt cookie storage (keyring)
- [ ] Scheduler daemon mode
- [ ] CI/CD with GitHub Actions

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
  config.json                           — User settings (AI key, default_platforms)
  schedule.json                         — Scheduled publish tasks
  history.jsonl                         — Publish history (JSONL, one record per line)
```

---

## Dev Commands

```bash
pip install -e ".[all,dev]"             # Install with all extras + test deps
playwright install chromium             # Required for browser-based publish

# Run tests
pytest -m "not flaky_network"           # Stable tests only (106)
pytest                                  # All tests including network-dependent

# Smoke test
social --help
social accounts
social login reddit                     # Instant from Chrome cookies
social reddit search "python" -n 3 --json
social twitter search "AI" -n 3 --json
social trending -p reddit,bilibili,twitter -n 3 --json
social publish "Test" -p reddit,twitter --dry-run
social -v reddit trending -n 2 --json   # With debug logging
```

---

## Key Dependencies (Optional)

| Package | Purpose | Install |
|---------|---------|---------|
| `browser-cookie3` | Extract cookies from Chrome/Firefox | `pip install socialcli[browser]` |
| `curl_cffi` | TLS fingerprint for Twitter GraphQL | `pip install socialcli[twitter]` |
| `xclienttransaction` | Twitter x-client-transaction-id header | included with `[twitter]` |
| `xhshow` | 小红书 API signing (x-s, x-s-common) | manual: `pip install xhshow` |
| `beautifulsoup4` | Twitter HTML parsing | included with `[twitter]` |

---

## Reference Materials

- `plan/socialcli-plan.md` — Full product spec, architecture, roadmap
- `plan/dev-plan-v2.md` — Sprint-based dev plan (current execution tracker)
- `github/twitter-cli/` — Twitter GraphQL + x-client-transaction reference
- `github/xiaohongshu-cli/` — XHS xhshow signing reference
- `github/rdt-cli/` — Reddit cookie auth reference
- `github/bilibili-cli/` — Bilibili API reference
