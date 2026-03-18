"""Facebook platform client — browser automation."""
from __future__ import annotations
from typing import List
import click
from socialcli.platforms.base import *
from socialcli.auth.cookie_store import load_cookies, cookie_string, load_account_info
from socialcli.auth.browser_login import browser_login

class FacebookPlatform(Platform):
    name = "facebook"
    display_name = "Facebook"
    icon = "📘"
    LOGIN_URL = "https://www.facebook.com/login/"
    SUCCESS_URL = "facebook.com"

    def login(self, account="default", **kw):
        return browser_login(self.name, self.LOGIN_URL, self.SUCCESS_URL, account, kw.get("headless", False))
    def check_login(self, account="default"):
        cookies = load_cookies(self.name, account)
        return bool(cookies and any(c.get("name") == "c_user" for c in cookies))
    def publish(self, content: Content, account="default") -> PublishResult:
        try:
            from socialcli.platforms.facebook.browser import facebook_publish
            return facebook_publish(content, account)
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))
    def search(self, query, account="default", **kw) -> List[SearchResult]:
        return []  # Facebook search requires complex auth
    def me(self, account="default"):
        info = load_account_info(self.name, account)
        if not info: return AccountInfo(platform=self.name, account=account, is_logged_in=False)
        return AccountInfo(platform=self.name, account=account, nickname=info.get("nickname", ""), user_id=info.get("user_id", ""), is_logged_in=True)

    @property
    def cli_group(self):
        platform = self  # capture for closures

        @click.group(name="facebook")
        def fb_group():
            """📘 Facebook — publish"""
            pass
        @fb_group.command()
        @click.argument("text")
        @click.option("--image", "-i", multiple=True)
        @click.option("--account", "-a", default="default")
        def publish(text, image, account):
            """Publish a Facebook post."""
            from socialcli.utils import output
            c = Content(text=text, images=list(image))
            r = platform.publish(c, account)
            if r.success: output.success(f"Posted: {r.url}")
            else: output.error(f"Failed: {r.error}")
        return fb_group
