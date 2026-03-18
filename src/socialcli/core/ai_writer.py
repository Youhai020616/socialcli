"""
AI content writer — generate and adapt content for different platforms.

Supports: OpenAI-compatible APIs (OpenAI, Claude via proxy, DeepSeek, etc.)
Config: social config set ai_api_key sk-xxx
        social config set ai_base_url https://api.openai.com/v1
        social config set ai_model gpt-4o-mini
"""
from __future__ import annotations

import json
import os
from typing import Optional

import httpx

from socialcli.core.content_adapter import PLATFORM_RULES

# Default config
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


def _get_config():
    """Load AI config from env or config file."""
    config_path = os.path.expanduser("~/.socialcli/config.json")
    file_config = {}
    if os.path.exists(config_path):
        try:
            file_config = json.loads(open(config_path).read())
        except Exception:
            pass

    return {
        "api_key": os.environ.get("OPENAI_API_KEY") or file_config.get("ai_api_key", ""),
        "base_url": os.environ.get("OPENAI_BASE_URL") or file_config.get("ai_base_url", DEFAULT_BASE_URL),
        "model": os.environ.get("AI_MODEL") or file_config.get("ai_model", DEFAULT_MODEL),
    }


def _chat(messages: list[dict], temperature: float = 0.7) -> str:
    """Call OpenAI-compatible chat API."""
    config = _get_config()
    if not config["api_key"]:
        raise RuntimeError(
            "AI API key not set. Configure with:\n"
            "  social config set ai_api_key sk-xxx\n"
            "  or export OPENAI_API_KEY=sk-xxx"
        )

    resp = httpx.post(
        f"{config['base_url']}/chat/completions",
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": config["model"],
            "messages": messages,
            "temperature": temperature,
        },
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"AI API error: {resp.status_code} {resp.text[:200]}")

    return resp.json()["choices"][0]["message"]["content"]


def generate(topic: str, platforms: list[str] = None) -> dict[str, str]:
    """
    Generate content for multiple platforms from a topic.

    Returns: {"douyin": "...", "twitter": "...", "reddit": "...", ...}
    """
    if not platforms:
        platforms = list(PLATFORM_RULES.keys())

    platform_specs = []
    for p in platforms:
        rules = PLATFORM_RULES.get(p, {})
        spec = f"- {p}: max {rules.get('max_text', 2000)} chars"
        if rules.get("merge_title_to_text"):
            spec += ", no separate title"
        if rules.get("format") == "markdown":
            spec += ", use Markdown"
        if p == "douyin":
            spec += ", Chinese, casual tone, add 话题标签"
        elif p == "xhs":
            spec += ", Chinese, add emoji, 种草风格"
        elif p == "twitter":
            spec += ", concise, add hashtags"
        elif p == "reddit":
            spec += ", detailed, informative, Markdown"
        elif p == "linkedin":
            spec += ", professional tone"
        platform_specs.append(spec)

    prompt = f"""Generate social media posts about: "{topic}"

Create one version for each platform, optimized for that platform's style and limits:
{chr(10).join(platform_specs)}

Return as JSON object with platform names as keys and post text as values.
Example: {{"twitter": "...", "reddit": "..."}}

Only return the JSON, no explanation."""

    result = _chat([{"role": "user", "content": prompt}])

    # Parse JSON from response
    try:
        # Handle markdown code blocks
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"raw": result}


def adapt(text: str, target_platform: str, source_platform: str = "") -> str:
    """
    Rewrite content to fit a target platform's style.
    """
    rules = PLATFORM_RULES.get(target_platform, {})

    style_hints = {
        "douyin": "Chinese, casual, short, trending hashtags with #",
        "xhs": "Chinese, emoji-rich, 种草/分享 style, hashtag with #话题#",
        "twitter": "English or bilingual, under 280 chars, hashtags, punchy",
        "reddit": "English, detailed, Markdown formatting, informative",
        "linkedin": "Professional, thoughtful, career/business focused",
        "tiktok": "Casual, trendy, hashtags, under 2200 chars",
        "bilibili": "Chinese, B站 style, 弹幕文化 tone",
    }

    style = style_hints.get(target_platform, "natural, engaging")
    max_len = rules.get("max_text", 2000)

    prompt = f"""Rewrite this content for {target_platform}:

Original:
{text}

Requirements:
- Style: {style}
- Max length: {max_len} characters
- Keep the core message
- Optimize for engagement on {target_platform}

Return only the rewritten text, no explanation."""

    return _chat([{"role": "user", "content": prompt}])


def suggest_tags(text: str, platform: str = "", count: int = 5) -> list[str]:
    """Generate hashtag suggestions for content."""
    prompt = f"""Suggest {count} hashtags for this social media post:

{text[:500]}

Platform: {platform or 'general'}
Return only the hashtags, one per line, without # prefix."""

    result = _chat([{"role": "user", "content": prompt}], temperature=0.5)
    tags = [line.strip().lstrip("#").strip() for line in result.strip().split("\n") if line.strip()]
    return tags[:count]
