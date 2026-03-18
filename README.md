<div align="center">

# 📱 SocialCLI

**Unified social media CLI — publish, search, and grow across all platforms.**

One command. Seven platforms. Zero API keys required.

[![PyPI](https://img.shields.io/pypi/v/socialcli?color=blue)](https://pypi.org/project/socialcli/)
[![Python](https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platforms](https://img.shields.io/badge/platforms-7-orange)](#supported-platforms)

[Install](#install) · [Quick Start](#quick-start) · [Platforms](#supported-platforms) · [Commands](#commands) · [AI Features](#ai-features) · [License](#license)

</div>

---

## Why

Social media managers juggle 5+ platforms daily. Existing tools either cost $50+/month, require complex API applications, or only support a few platforms.

SocialCLI takes a different approach:

- **No API keys** — uses browser automation and reverse-engineered APIs
- **No monthly fees** — open source, runs on your machine
- **All major platforms** — Chinese + international, one unified interface
- **Server-ready** — runs headless on servers for 24/7 automation
- **AI-powered** — generate platform-optimized content from a single topic

## Supported Platforms

| Platform | Login | Publish | Search | Trending | Interact |
|----------|:-----:|:-------:|:------:|:--------:|:--------:|
| 🎬 **Douyin** (抖音) | QR scan | ✅ | ✅ | ✅ | — |
| 📕 **Xiaohongshu** (小红书) | QR scan | ✅ | ✅ | — | — |
| 🐦 **Twitter/X** | Browser | ✅ | ✅ | ✅ | — |
| 📖 **Reddit** | Browser | ✅ | ✅ | ✅ | ✅ upvote, comment |
| 🎵 **TikTok** | Browser | ✅ | ✅ | ✅ | — |
| 💼 **LinkedIn** | Browser | ✅ | ✅ | — | — |
| 📺 **Bilibili** (B站) | QR scan | ✅ | ✅ | ✅ | — |

## Install

```bash
pip install socialcli
playwright install chromium
```

Or from source:

```bash
git clone https://github.com/Youhai020616/socialcli.git
cd socialcli
pip install -e .
playwright install chromium
```

## Quick Start

```bash
# 1. Login to platforms (one-time, opens browser)
social login douyin
social login twitter
social login reddit

# 2. Publish to all platforms at once
social publish "My new blog post! 🚀" \
  --image cover.jpg \
  -p douyin,twitter,reddit

# 3. Search across platforms
social douyin search "美食"
social twitter search "AI tools"
social reddit search "programming" -r python

# 4. Check what's trending
social trending -p douyin,twitter,bilibili
```

## Commands

### Cross-Platform

| Command | Description |
|---------|-------------|
| `social publish` | Publish to one or all platforms |
| `social trending` | Aggregated trending from all platforms |
| `social monitor` | Watch keywords across platforms in real-time |
| `social batch` | Batch publish from CSV, JSON, or directory |
| `social schedule` | Manage scheduled posts |
| `social login` | Login to a platform |
| `social accounts` | List all logged-in accounts |
| `social ai` | AI content generation and adaptation |

### Per-Platform

Every platform supports its own subcommands:

```bash
social <platform> search <query>
social <platform> publish [options]
social <platform> trending
```

---

## Usage

### Publish

```bash
# Single platform
social publish "Hello World!" -p twitter

# Multiple platforms
social publish -t "Title" -v video.mp4 -p douyin,tiktok,bilibili

# All platforms
social publish --file post.md -p all

# With images, tags, and link
social publish "Check this out!" \
  -i photo1.jpg -i photo2.jpg \
  --tags "coding,AI,startup" \
  --link https://myblog.com \
  -p twitter,linkedin,reddit

# Reddit with subreddit
social publish "Look what I built" \
  -p reddit \
  -r programming \
  -t "Show HN: SocialCLI"

# Schedule for later
social publish "Good morning! ☀️" \
  -p twitter,linkedin \
  --schedule "2026-04-01T09:00:00"

# Preview without posting
social publish "Test" -p all --dry-run
```

Content is automatically adapted per platform:
- **Douyin/TikTok**: video-first, Chinese hashtags
- **Xiaohongshu**: image-first, emoji, 种草 style
- **Twitter**: truncated to 280 chars, hashtags
- **Reddit**: Markdown body, subreddit targeting
- **LinkedIn**: professional tone
- **Bilibili**: video with tags

### Search

```bash
social douyin search "美食"
social douyin search "编程" --sort 最多点赞

social xhs search "咖啡" --sort popularity_descending

social twitter search "AI startups" --count 30 --json

social reddit search "rust vs go" -r programming --sort top

social bilibili search "教程" --json

social tiktok search "cooking" --count 10
```

### Trending

```bash
# All platforms at once
social trending

# Specific platforms
social trending -p douyin,twitter,bilibili

# JSON output
social trending -p douyin --json

# Per-platform
social douyin trending
social twitter trending
social reddit trending
social bilibili trending
```

### Monitor

Watch for keyword mentions across platforms in real-time:

```bash
# Monitor your brand
social monitor -k "my-product,my-brand" -p twitter,reddit

# Monitor competitors
social monitor -k "competitor-name" -p all -i 120

# Limited checks
social monitor -k "AI tools" -p reddit -n 10
```

### Batch Publish

```bash
# From CSV
social batch posts.csv

# From JSON
social batch posts.json --dry-run

# From directory (each .md file = one post)
social batch ./content/ -p twitter,reddit,linkedin
```

CSV format:

```csv
platform,title,content,image,video,tags,subreddit
twitter,,Hello from CSV!,photo.jpg,,coding,
reddit,My Post,Post body in Markdown,,,python,programming
douyin,标题,描述,,video.mp4,美食;分享,
```

### Schedule

```bash
# Publish with schedule
social publish "Scheduled post" -p twitter --schedule "2026-04-01T09:00:00"

# List scheduled tasks
social schedule list

# Execute due tasks
social schedule run

# Remove a task
social schedule remove <task-id>
```

### Interactive REPL

```bash
social douyin search "关键词"      # search and browse
social reddit trending             # check hot posts
social twitter search "topic"      # find discussions
```

## AI Features

Generate and adapt content using OpenAI-compatible APIs:

```bash
# Setup
social config set ai_api_key sk-xxx
social config set ai_model gpt-4o-mini
# Or: export OPENAI_API_KEY=sk-xxx

# Generate content for all platforms from a single topic
social ai generate "AI coding tools" -p twitter,reddit,xhs

# Adapt existing content for a specific platform
social ai adapt "My long article about..." -p twitter

# Suggest hashtags
social ai tags "My post about web development" -p twitter
```

AI generates platform-optimized content:
- **Twitter**: concise, under 280 chars, with hashtags
- **Xiaohongshu**: Chinese, emoji-rich, 种草 style
- **Reddit**: detailed, Markdown, informative
- **LinkedIn**: professional tone

## Login

SocialCLI uses browser-based login. Your credentials stay in your browser — we only capture cookies.

```bash
social login douyin       # Opens browser → scan QR code
social login xhs          # Opens browser → scan QR code
social login twitter      # Opens browser → enter credentials
social login reddit       # Opens browser → enter credentials
social login tiktok       # Opens browser → login
social login linkedin     # Opens browser → login
social login bilibili     # Opens browser → scan QR code

social accounts           # View all logged-in accounts
```

Cookies are stored locally at `~/.socialcli/accounts/`.

## Architecture

```
socialcli/
├── platforms/                    # Platform adapters
│   ├── base.py                   #   Platform interface (login/publish/search/trending)
│   ├── registry.py               #   Auto-discovery registry
│   ├── douyin/                   #   Reverse-engineered API + Playwright
│   ├── xiaohongshu/              #   CDP automation
│   ├── twitter/                  #   GraphQL API + cookie auth
│   ├── reddit/                   #   JSON API + cookie auth
│   ├── tiktok/                   #   API + Playwright upload
│   ├── linkedin/                 #   Voyager API + Playwright
│   └── bilibili/                 #   Public API + Playwright upload
├── core/
│   ├── publisher.py              #   Multi-platform publish engine
│   ├── content_adapter.py        #   Auto-format content per platform
│   ├── scheduler.py              #   Scheduled publishing
│   ├── ai_writer.py              #   AI content generation
│   ├── batch.py                  #   Batch operations
│   └── monitor.py                #   Keyword monitoring
├── auth/
│   ├── browser_login.py          #   Browser-based login (Playwright)
│   └── cookie_store.py           #   Cookie persistence
└── commands/                     #   Click CLI commands
```

### How It Works

```
┌──────────────┐
│  social CLI   │  ← You type commands
└──────┬───────┘
       │
┌──────▼───────┐
│  Publisher    │  ← Adapts content per platform
└──────┬───────┘
       │
┌──────▼───────────────────────────────┐
│  Platform Adapters                    │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ Douyin  │ │ Twitter │ │ Reddit │ │  ← Each platform has:
│  │ API +   │ │ GraphQL │ │ JSON   │ │     1. Reverse-engineered API (fast)
│  │ Browser │ │ + Cookie│ │ + Cook │ │     2. Browser automation (upload)
│  └─────────┘ └─────────┘ └────────┘ │     3. Cookie-based auth
└──────────────────────────────────────┘
```

No official APIs. No API keys. No rate limit applications.

## Configuration

```bash
# View all settings
social config show

# Set defaults
social config set default_platforms twitter,reddit
social config set ai_api_key sk-xxx
social config set ai_model gpt-4o-mini
```

Config stored at `~/.socialcli/config.json`.

## Comparison

|  | SocialCLI | AiToEarn | Buffer | Hootsuite |
|--|-----------|----------|--------|-----------|
| Type | CLI | Desktop App | Web SaaS | Web SaaS |
| Platforms | 7 | 14 | 6 | 6 |
| API Required | No | No | Yes | Yes |
| Price | Free (OSS) | Free (OSS) | $6-120/mo | $99-739/mo |
| Server Deploy | ✅ | ❌ | ✅ | ✅ |
| AI Content | ✅ | ✅ | ✅ | ✅ |
| Open Source | ✅ | ✅ | ❌ | ❌ |
| Install | `pip install` | Desktop installer | Browser | Browser |

## Disclaimer

This tool is for educational and personal use. When using SocialCLI to interact with any social media platform, you must comply with that platform's Terms of Service. Any account restrictions or bans resulting from the use of this tool are the user's own responsibility.

## Contributing

Contributions are welcome! To add a new platform:

1. Create `platforms/<name>/client.py` implementing the `Platform` base class
2. Create `platforms/<name>/browser.py` for Playwright automation
3. Register in `platforms/<name>/__init__.py`
4. Add to `platforms/registry.py` → `load_all()`
5. Submit a PR

## License

[MIT](LICENSE)
