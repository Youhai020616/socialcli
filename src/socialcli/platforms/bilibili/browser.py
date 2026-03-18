"""Bilibili video upload via bilibili-api-python (pure API, no browser)."""
from __future__ import annotations

import asyncio
import logging
import os

from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

logger = logging.getLogger(__name__)


def _extract_cover(video_path: str) -> str:
    """Extract first frame from video as cover image. Returns path or empty string."""
    import subprocess
    import tempfile

    cover_path = os.path.join(tempfile.gettempdir(), "socialcli_cover.jpg")
    try:
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vframes", "1", "-y", "-q:v", "2", cover_path],
            capture_output=True, timeout=15,
        )
        if os.path.exists(cover_path) and os.path.getsize(cover_path) > 0:
            logger.debug("bilibili: extracted cover from video → %s", cover_path)
            return cover_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("bilibili: ffmpeg not available or timeout, skipping cover")

    # Fallback: create minimal JPEG
    try:
        # Minimal valid JPEG (1x1 black pixel)
        import struct
        with open(cover_path, "wb") as f:
            f.write(
                b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
                b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
                b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
                b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
                b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
                b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00'
                b'\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
                b'\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04'
                b'\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07'
                b'\x22q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16'
                b'\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83'
                b'\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a'
                b'\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8'
                b'\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6'
                b'\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2'
                b'\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa'
                b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\xa8\xa3\x80\x0f\xff\xd9'
            )
        return cover_path
    except Exception:
        return ""


def bilibili_publish(content: Content, account: str = "default") -> PublishResult:
    """Publish video to Bilibili via API."""
    return asyncio.run(_publish_async(content, account))


async def _publish_async(content: Content, account: str) -> PublishResult:
    try:
        from bilibili_api import video_uploader
        from bilibili_api.video_uploader import VideoMeta
        from bilibili_api.utils.network import Credential
    except ImportError:
        return PublishResult(
            success=False, platform="bilibili",
            error="bilibili-api-python not installed. Run: pip install bilibili-api-python",
        )

    # Build credential from saved cookies
    cookies = load_cookies("bilibili", account)
    if not cookies:
        return PublishResult(success=False, platform="bilibili", error="Not logged in. Run: social login bilibili")

    cookie_dict = {c["name"]: c["value"] for c in cookies if "name" in c}

    sessdata = cookie_dict.get("SESSDATA", "")
    bili_jct = cookie_dict.get("bili_jct", "")
    buvid3 = cookie_dict.get("buvid3", "")
    dedeuserid = cookie_dict.get("DedeUserID", "")

    if not sessdata or not bili_jct:
        return PublishResult(
            success=False, platform="bilibili",
            error="Missing SESSDATA or bili_jct cookie. Run: social login bilibili",
        )

    credential = Credential(
        sessdata=sessdata,
        bili_jct=bili_jct,
        buvid3=buvid3,
        dedeuserid=dedeuserid,
    )

    # Build upload page
    import os
    if not os.path.exists(content.video):
        return PublishResult(success=False, platform="bilibili", error=f"Video not found: {content.video}")

    title = content.title or os.path.splitext(os.path.basename(content.video))[0]

    page = video_uploader.VideoUploaderPage(
        path=content.video,
        title=title[:80],
        description=content.text[:2000] if content.text else "",
    )

    # Generate cover from video first frame
    cover_path = _extract_cover(content.video)

    # Build metadata using VideoMeta (avoids API field mismatch)
    tags_list = content.tags[:10] if content.tags else [title[:20]]
    meta = VideoMeta(
        tid=174,  # 生活 > 其他
        title=title[:80],
        desc=content.text[:2000] if content.text else title,
        cover=cover_path,
        tags=tags_list,
        original=True,
    )

    uploader = video_uploader.VideoUploader(
        pages=[page],
        meta=meta,
        credential=credential,
    )

    # Progress logging
    @uploader.on("__ALL__")
    async def on_event(data: dict):
        event = data.get("name", "")
        if "PRE_UPLOAD" in event:
            logger.info("bilibili: preparing upload...")
        elif "PREUPLOAD_DONE" in event:
            logger.info("bilibili: upload started")
        elif "PRE_PAGE" in event:
            logger.info("bilibili: uploading video...")
        elif "PAGE_DONE" in event:
            logger.info("bilibili: video uploaded, submitting...")
        elif "SUBMIT_DONE" in event:
            logger.info("bilibili: submit complete!")

    try:
        logger.info("bilibili: starting upload of %s", content.video)
        result = await uploader.start()

        bvid = result.get("bvid", "")
        aid = result.get("aid", "")

        url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
        logger.info("bilibili: published %s", url)

        return PublishResult(
            success=True,
            platform="bilibili",
            post_id=bvid or str(aid),
            url=url,
        )
    except Exception as e:
        error_msg = str(e)
        if "credential" in error_msg.lower() or "-101" in error_msg:
            error_msg = f"Cookie expired. Run: social login bilibili (原始错误: {error_msg})"
        return PublishResult(success=False, platform="bilibili", error=error_msg)
