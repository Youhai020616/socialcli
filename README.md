# 📱 socialcli

Unified social media CLI — publish, search, trending across all platforms.

## Install

```bash
pip install -e .
playwright install chromium
```

## Quick Start

```bash
social login douyin              # QR scan login
social login xhs                 # QR scan login
social accounts                  # List logged-in accounts

social douyin search "美食"       # Search Douyin
social douyin trending           # Douyin hot search
social xhs search "咖啡"         # Search Xiaohongshu

# Publish to multiple platforms
social publish "Hello World!" -p douyin,xhs -i cover.jpg
```

## License

MIT
