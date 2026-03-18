"""Threads platform client — browser automation."""
from __future__ import annotations
from typing import List
import click
from socialcli.platforms.base import *
from socialcli.auth.cookie_store import load_cookies
from socialcli.auth.browser_login import browser_login

class ThreadsPlatform(Platform):
    name = "threads"
    display_name = "Threads"
    icon = "🧵"
    LOGIN_URL = "https://www.threads.net/login"
    SUCCESS_URL = "threads.net"

    def login(self, account="default", **kw):
        return browser_login(self.name, self.LOGIN_URL, self.SUCCESS_URL, account, kw.get("headless", False))
    def check_login(self, account="default"):
        cookies = load_cookies(self.name, account)
        return bool(cookies and len(cookies) > 3)
    def publish(self, content: Content, account="default") -> PublishResult:
        try:
            from socialcli.platforms.threads.browser import threads_publish
            return threads_publish(content, account)
        except Exception as e:
            return PublishResult(success=False, platform=self.name, error=str(e))
    def search(self, query, account="default", **kw) -> List[SearchResult]:
        return []  # Threads search is limited

    @property
    def cli_group(self):
        platform = self  # capture for closures

        @click.group(name="threads")
        def th_group():
            """🧵 Threads — publish"""
            pass
        @th_group.command()
        @click.argument("text")
        @click.option("--image", "-i", multiple=True)
        @click.option("--account", "-a", default="default")
        def publish(text, image, account):
            """Publish a thread."""
            from socialcli.utils import output
            c = Content(text=text, images=list(image))
            r = platform.publish(c, account)
            if r.success: output.success(f"Posted: {r.url}")
            else: output.error(f"Failed: {r.error}")
        return th_group
