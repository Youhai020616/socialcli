"""Instagram platform client — browser automation."""
from __future__ import annotations
from typing import List
import click
from socialcli.platforms.base import *
from socialcli.auth.cookie_store import load_cookies, load_account_info
from socialcli.auth.browser_login import browser_login

class InstagramPlatform(Platform):
    name = "instagram"
    display_name = "Instagram"
    icon = "📷"
    LOGIN_URL = "https://www.instagram.com/accounts/login/"
    SUCCESS_URL = "instagram.com"

    def login(self, account="default", **kw):
        return browser_login(self.name, self.LOGIN_URL, self.SUCCESS_URL, account, kw.get("headless", False))
    def check_login(self, account="default"):
        cookies = load_cookies(self.name, account)
        return bool(cookies and any(c.get("name") == "sessionid" for c in cookies))
    def publish(self, content: Content, account="default") -> PublishResult:
        if not content.images and not content.video:
            return PublishResult(success=False, platform=self.name, error="Instagram requires image or video")
        try:
            from socialcli.platforms.instagram.browser import instagram_publish
            return instagram_publish(content, account)
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))
    def search(self, query, account="default", **kw) -> List[SearchResult]:
        return []  # Instagram search requires complex GraphQL
    def me(self, account="default"):
        info = load_account_info(self.name, account)
        if not info: return AccountInfo(platform=self.name, account=account, is_logged_in=False)
        return AccountInfo(platform=self.name, account=account, nickname=info.get("nickname", ""), user_id=info.get("user_id", ""), is_logged_in=True)

    @property
    def cli_group(self):
        platform = self  # capture for closures

        @click.group(name="instagram")
        def ig_group():
            """📷 Instagram — publish"""
            pass
        @ig_group.command()
        @click.option("--caption", "-c", default="", help="Post caption")
        @click.option("--image", "-i", multiple=True, help="Image files")
        @click.option("--video", "-v", default="", help="Video file (Reel)")
        @click.option("--account", "-a", default="default")
        def publish(caption, image, video, account):
            """Publish to Instagram."""
            from socialcli.utils import output
            c = Content(text=caption, images=list(image), video=video)
            r = platform.publish(c, account)
            if r.success: output.success(f"Posted: {r.url}")
            else: output.error(f"Failed: {r.error}")
        return ig_group
