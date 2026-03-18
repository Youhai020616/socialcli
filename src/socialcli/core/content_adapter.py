"""
Content adapter — convert unified Content to platform-specific format.
"""
from __future__ import annotations

import copy
from socialcli.platforms.base import Content

PLATFORM_RULES = {
    "douyin": {
        "max_title": 30,
        "max_text": 2000,
        "media": "video_first",
        "tag_prefix": "#",
        "tag_suffix": " ",
        "supports_video": True,
        "supports_images": True,
    },
    "xiaohongshu": {
        "max_title": 20,
        "max_text": 1000,
        "media": "image_first",
        "tag_prefix": "#",
        "tag_suffix": "[话题]# ",
        "supports_video": True,
        "supports_images": True,
    },
    "twitter": {
        "max_title": 0,  # No separate title
        "max_text": 280,
        "media": "image_optional",
        "tag_prefix": "#",
        "tag_suffix": " ",
        "supports_video": True,
        "supports_images": True,
        "merge_title_to_text": True,
    },
    "reddit": {
        "max_title": 300,
        "max_text": 40000,
        "media": "link_or_image",
        "format": "markdown",
        "supports_video": False,
        "supports_images": True,
        "requires_subreddit": True,
    },
    "tiktok": {
        "max_title": 0,
        "max_text": 2200,
        "media": "video_required",
        "tag_prefix": "#",
        "tag_suffix": " ",
        "supports_video": True,
        "supports_images": False,
        "merge_title_to_text": True,
    },
    "linkedin": {
        "max_title": 0,
        "max_text": 3000,
        "media": "image_optional",
        "tone": "professional",
        "supports_video": True,
        "supports_images": True,
        "merge_title_to_text": True,
    },
    "bilibili": {
        "max_title": 80,
        "max_text": 2000,
        "media": "video_first",
        "tag_prefix": "",
        "tag_suffix": "",
        "supports_video": True,
        "supports_images": True,
    },
    "weibo": {
        "max_title": 0,
        "max_text": 2000,
        "media": "image_optional",
        "tag_prefix": "#",
        "tag_suffix": "#",
        "supports_video": True,
        "supports_images": True,
        "merge_title_to_text": True,
    },
    "kuaishou": {
        "max_title": 30,
        "max_text": 2000,
        "media": "video_required",
        "tag_prefix": "#",
        "tag_suffix": " ",
        "supports_video": True,
        "supports_images": False,
    },
    "youtube": {
        "max_title": 100,
        "max_text": 5000,
        "media": "video_required",
        "tag_prefix": "",
        "tag_suffix": "",
        "supports_video": True,
        "supports_images": False,
    },
    "facebook": {
        "max_title": 0,
        "max_text": 63206,
        "media": "image_optional",
        "merge_title_to_text": True,
        "supports_video": True,
        "supports_images": True,
    },
    "instagram": {
        "max_title": 0,
        "max_text": 2200,
        "media": "image_required",
        "tag_prefix": "#",
        "tag_suffix": " ",
        "merge_title_to_text": True,
        "supports_video": True,
        "supports_images": True,
    },
    "threads": {
        "max_title": 0,
        "max_text": 500,
        "media": "image_optional",
        "merge_title_to_text": True,
        "supports_video": False,
        "supports_images": True,
    },
}


def adapt(content: Content, platform: str) -> Content:
    """Adapt content to a specific platform's requirements."""
    rules = PLATFORM_RULES.get(platform, {})
    adapted = Content(**content.__dict__)
    adapted.extras = dict(content.extras)

    # Merge title into text for platforms without separate title
    if rules.get("merge_title_to_text") and adapted.title:
        adapted.text = f"{adapted.title}\n\n{adapted.text}" if adapted.text else adapted.title
        adapted.title = ""

    # Truncate title
    max_title = rules.get("max_title", 200)
    if max_title > 0 and len(adapted.title) > max_title:
        adapted.title = adapted.title[: max_title - 3] + "..."

    # Truncate text
    max_text = rules.get("max_text", 10000)
    if len(adapted.text) > max_text:
        adapted.text = adapted.text[: max_text - 3] + "..."

    # Format tags
    if adapted.tags:
        prefix = rules.get("tag_prefix", "#")
        suffix = rules.get("tag_suffix", " ")
        formatted_tags = " ".join(f"{prefix}{tag}{suffix}" for tag in adapted.tags)
        # Append tags to text if room
        if len(adapted.text) + len(formatted_tags) + 2 <= max_text:
            adapted.text = f"{adapted.text}\n\n{formatted_tags}".strip()

    # Add link to text if provided
    if adapted.link and platform in ("twitter", "reddit", "linkedin"):
        if len(adapted.text) + len(adapted.link) + 2 <= max_text:
            adapted.text = f"{adapted.text}\n\n{adapted.link}".strip()

    return adapted


def validate(content: Content, platform: str) -> list[str]:
    """Validate content against platform rules. Returns list of warnings."""
    rules = PLATFORM_RULES.get(platform, {})
    warnings = []

    if rules.get("media") == "video_required" and not content.video:
        warnings.append(f"{platform} requires a video")

    if rules.get("requires_subreddit") and not content.extras.get("subreddit"):
        warnings.append(f"{platform} requires a subreddit (--subreddit / -r)")

    if not content.title and not content.text and not content.images and not content.video:
        warnings.append("Content is empty")

    return warnings
