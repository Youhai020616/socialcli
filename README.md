<div align="center">

# 📱 SocialCLI

**Unified social media CLI — publish, search, and grow across all platforms.**

One command. Multiple platforms. Zero API keys required.

[![Python](https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-112%20passing-brightgreen)](#)
[![Platforms](https://img.shields.io/badge/platforms-13-orange)](#supported-platforms)

[Install](#install) · [Quick Start](#quick-start) · [Platforms](#supported-platforms) · [Commands](#commands) · [AI Features](#ai-features) · [License](#license)

</div>

---

## Why

Social media managers juggle 5+ platforms daily. Existing tools either cost $50+/month, require complex API applications, or only support a few platforms.

SocialCLI takes a different approach:

- **No API keys** — uses browser cookie extraction and reverse-engineered APIs
- **No monthly fees** — open source, runs on your machine
- **Instant login** — extracts cookies from your Chrome/Firefox, no browser popups
- **Cross-platform publish** — one command posts to Reddit + Twitter simultaneously
- **All major platforms** — Chinese + international, one unified interface
- **AI-powered** — generate platform-optimized content from a single topic

## Supported Platforms

### Fully Working ✅

| Platform | Login | Search | Trending | Publish |
|----------|:-----:|:------:|:--------:|:-------:|
| 📖 **Reddit** | ✅ Instant | ✅ | ✅ | ✅ Verified |
| 🐦 **Twitter/X** | ✅ Instant | ✅ | ✅ | ✅ Verified |
| 📺 **Bilibili** (B站) | ✅ Instant | ✅ | ✅ | 🔧 Playwright |

### Login + Partial API

| Platform | Login | Search | Trending | Notes |
|----------|:-----:|:------:|:--------:|:------|
| 📕 **Xiaohongshu** (小红书) | ✅ Instant | 🔧 | — | API signing integrated (xhshow) |
| 💼 **LinkedIn** | ✅ Instant | 🔧 | — | Voyager API auth verified |
| 🎬 **Douyin** (抖音) | 🔧 | 🔧 | 🔧 | Needs anti-crawl signatures |
| 🎵 **TikTok** | 🔧 | 🔧 | 🔧 | Needs signatures |
| 🔥 **Weibo** (微博) | 🔧 | 🔧 | 🔧 | Skeleton |
| ⚡ **Kuaishou** (快手) | 🔧 | 🔧 | 🔧 | Skeleton |
| ▶️ **YouTube** | 🔧 | 🔧 | 🔧 | Skeleton |
| 📘 **Facebook** | 🔧 | — | — | Skeleton |
| 📷 **Instagram** | 🔧 | — | — | Skeleton |
| 🧵 **Threads** | 🔧 | — | — | Skeleton |

> **✅ Instant Login**: Uses `browser-cookie3` to extract cookies from your local browser — zero manual input, instant auth.

## Install

```bash
# From source (recommended for now)
git clone https://github.com/Youhai020616/socialcli.git
cd socialcli
pip install -e ".[all]"
playwright install chromium
```

Optional extras:

```bash
pip install -e ".[browser]"    # Instant login from Chrome cookies
pip install -e ".[twitter]"    # Twitter GraphQL (curl_cffi + TLS fingerprint)
pip install -e ".[all]"        # Everything (browser + twitter + AI)
```

## Quick Start

```bash
# 1. Login — instant, extracts from your Chrome
social login reddit
social login twitter
social login bilibili

# 2. Check accounts
social accounts
social accounts --check    # Verify cookies still valid

# 3. Search across platforms
social reddit search "python programming" -n 5
social twitter search "AI tools" -n 5
social bilibili search "编程教程" -n 5

# 4. Check what's trending
social trending -p reddit,twitter,bilibili -n 5

# 5. Publish to multiple platforms at once
social publish "My new blog post! 🚀" \
  -t "Check This Out" \
  -p reddit,twitter \
  -r programming

# 6. Preview without posting
social publish "Test" -p reddit,twitter,bilibili --dry-run
```

## Commands

### Cross-Platform

| Command | Description |
|---------|-------------|
| `social publish` | Publish to one or all platforms (parallel) |
| `social trending` | Aggregated trending from multiple platforms |
| `social login` | Login to a platform (instant from browser cookies) |
| `social logout` | Remove saved credentials |
| `social accounts` | List logged-in accounts (`--check` to verify) |
| `social history` | View publish history |
| `social schedule` | Manage scheduled posts |
| `social config` | View and set configuration |
| `social batch` | Batch publish from CSV, JSON, or directory |
| `social monitor` | Watch keywords across platforms |
| `social ai` | AI content generation and adaptation |

### Per-Platform

```bash
social <platform> search <query>     # Search
social <platform> trending           # Platform trending
social <platform> publish [options]  # Platform-specific publish
```

---

## Usage

### Publish

```bash
# Single platform
social publish "Hello World!" -p twitter

# Multiple platforms (publishes in parallel)
social publish "Cross-post this!" -t "My Title" -p reddit,twitter -r programming

# From Markdown file
social publish -f post.md -p reddit,twitter --dry-run

# With images, tags, and link
social publish "Check this out!" \
  -i photo1.jpg -i photo2.jpg \
  --tags "coding,AI,startup" \
  --link https://myblog.com \
  -p twitter,reddit

# Reddit with subreddit
social publish "Look what I built" \
  -p reddit -r programming \
  -t "Show HN: SocialCLI"

# Schedule for later
social publish "Good morning! ☀️" \
  -p twitter \
  --schedule "2026-04-01T09:00:00"

# Preview without posting
social publish "Test" -p all --dry-run
```

Content is automatically adapted per platform:
- **Twitter**: title merged into text, truncated to 280 chars, hashtags appended
- **Reddit**: title and body kept separate, Markdown format, subreddit targeting
- **Bilibili**: video-first, tags formatted for B站
- **Xiaohongshu**: image-first, emoji, 种草 style

### Search

```bash
social reddit search "rust vs go" -r programming --sort top
social twitter search "AI startups" -n 10 --json
social bilibili search "编程教程" -n 5 --json
```

### Trending

```bash
# Aggregated from multiple platforms
social trending -p reddit,twitter,bilibili -n 10

# JSON output
social trending -p twitter --json

# Single platform
social reddit trending -n 5
social twitter trending -n 5
social bilibili trending -n 5
```

### History

```bash
# View recent publishes
social history

# Filter by platform
social history -p reddit -n 10

# JSON output
social history --json
```

### Schedule

```bash
# Schedule a post
social publish "Scheduled post" -p twitter --schedule "2026-04-01T09:00:00"

# List scheduled tasks
social schedule list

# Execute due tasks
social schedule run

# Remove a task
social schedule remove <task-id>
```

### Batch Publish

```bash
# From CSV
social batch posts.csv

# From JSON
social batch posts.json --dry-run

# From directory (each .md file = one post)
social batch ./content/ -p twitter,reddit
```

CSV format:

```csv
platform,title,content,image,video,tags,subreddit
twitter,,Hello from CSV!,photo.jpg,,coding,
reddit,My Post,Post body in Markdown,,,python,programming
```

### Monitor

```bash
# Monitor keywords across platforms
social monitor -k "my-product,my-brand" -p twitter,reddit

# With interval
social monitor -k "AI tools" -p reddit -n 10 -i 120
```

## AI Features

Generate and adapt content using OpenAI-compatible APIs:

```bash
# Setup
social config set ai_api_key sk-xxx
social config set ai_model gpt-4o-mini

# Generate content for multiple platforms
social ai generate "AI coding tools" -p twitter,reddit,xhs

# Adapt existing content for a platform
social ai adapt "My long article about..." -p twitter

# Suggest hashtags
social ai tags "My post about web development" -p twitter
```

## Login

SocialCLI extracts cookies from your local browser — **no password entry needed**.

```bash
social login reddit       # Instant — reads Chrome cookies
social login twitter      # Instant — reads Chrome cookies
social login bilibili     # Instant — reads Chrome cookies
social login xhs          # Instant — reads Chrome cookies
social login linkedin     # Instant — reads Chrome cookies

social accounts           # View all logged-in accounts
social accounts --check   # Verify cookies are still valid
social logout reddit      # Remove saved cookies
```

> **How it works**: If you're logged into Reddit/Twitter/etc. in your Chrome browser, SocialCLI extracts those cookies instantly. No browser popup, no QR code, no password. Falls back to Playwright browser login if extraction fails.

Cookies are stored locally at `~/.socialcli/accounts/`.

## Configuration

```bash
social config show                                    # View all settings
social config set default_platforms twitter,reddit     # Set defaults
social config set ai_api_key sk-xxx                   # AI API key
social config set ai_model gpt-4o-mini                # AI model
social config unset ai_api_key                        # Remove a setting
```

Config stored at `~/.socialcli/config.json`.

## Architecture

```
socialcli/
├── platforms/                    # Platform adapters (13 platforms)
│   ├── base.py                   #   Platform ABC + data models + browser cookie extraction
│   ├── registry.py               #   Auto-discovery registry
│   ├── reddit/client.py          #   Cookie auth + modhash + JSON API
│   ├── twitter/client.py         #   GraphQL + curl_cffi + x-client-transaction-id
│   ├── bilibili/client.py        #   Public API + Playwright upload
│   ├── xiaohongshu/client.py     #   xhshow signing + Playwright
│   └── ...                       #   7 more platform adapters
├── core/
│   ├── publisher.py              #   Parallel multi-platform publish (ThreadPoolExecutor)
│   ├── content_adapter.py        #   Auto-format content per platform (13 rule sets)
│   ├── scheduler.py              #   Scheduled publishing (JSON storage)
│   ├── ai_writer.py              #   AI content generation (OpenAI-compatible)
│   ├── batch.py                  #   Batch operations (CSV/JSON/directory)
│   └── monitor.py                #   Keyword monitoring
├── auth/
│   ├── browser_login.py          #   Playwright browser login (fallback)
│   └── cookie_store.py           #   Cookie persistence (~/.socialcli/accounts/)
├── commands/                     #   12 Click CLI commands
└── tests/                        #   112 tests (10 test files)
```

### How It Works

```
┌──────────────────┐
│  social CLI       │  ← You type commands
└──────┬───────────┘
       │
┌──────▼───────────┐
│  browser-cookie3  │  ← Extracts cookies from Chrome/Firefox (instant)
└──────┬───────────┘
       │
┌──────▼───────────┐
│  Content Adapter  │  ← Adapts content per platform rules
└──────┬───────────┘
       │
┌──────▼───────────────────────────────┐
│  Parallel Publisher (ThreadPool)      │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ Reddit  │ │ Twitter │ │Bilibili│ │  ← Simultaneous publish
│  │ JSON API│ │ GraphQL │ │ Public │ │     Cookie-based auth
│  │ +modhash│ │+curl_cffi│ │  API  │ │     No official APIs
│  └─────────┘ └─────────┘ └────────┘ │
└──────────────────────────────────────┘
```

## Comparison

|  | SocialCLI | AiToEarn | Buffer | Hootsuite |
|--|-----------|----------|--------|-----------|
| Type | CLI | Desktop App | Web SaaS | Web SaaS |
| Platforms | 13 | 14 | 6 | 6 |
| API Required | No | No | Yes | Yes |
| Price | Free (OSS) | Free (OSS) | $6-120/mo | $99-739/mo |
| Parallel Publish | ✅ | ❌ | ✅ | ✅ |
| Server Deploy | ✅ | ❌ | ✅ | ✅ |
| AI Content | ✅ | ✅ | ✅ | ✅ |
| Open Source | ✅ | ✅ | ❌ | ❌ |
| Install | `pip install` | Desktop | Browser | Browser |
| Login Method | Cookie extract | Browser | OAuth | OAuth |

## Development

```bash
# Setup
git clone https://github.com/Youhai020616/socialcli.git
cd socialcli
pip install -e ".[all,dev]"
playwright install chromium

# Run tests
pytest -m "not flaky_network"     # 109 stable tests
pytest                            # All 112 tests

# Smoke test
social --help
social login reddit
social reddit search "python" -n 3 --json
social publish "Test" -p reddit --dry-run
```

## Contributing

Contributions are welcome! To add a new platform:

1. Create `platforms/<name>/client.py` extending `Platform` base class
2. Set `cookie_domain` and `required_cookies` for browser cookie extraction
3. Implement `login`, `check_login`, `publish`, `search`
4. Add `cli_group` property with Click subcommands
5. Register in `platforms/<name>/__init__.py`
6. Add to `registry.load_all()` and `content_adapter.PLATFORM_RULES`
7. Write tests

## Disclaimer

This tool is for educational and personal use. When using SocialCLI to interact with any social media platform, you must comply with that platform's Terms of Service. Any account restrictions or bans resulting from the use of this tool are the user's own responsibility.

## License

[MIT](LICENSE)
