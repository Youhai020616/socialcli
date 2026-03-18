"""
Xiaohongshu Playwright browser automation — publish notes.
"""
from __future__ import annotations

import asyncio
import os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

CREATOR_URL = "https://creator.xiaohongshu.com/publish/publish"


def xhs_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_publish_async(content, account))


async def _publish_async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright

    cookies = load_cookies("xhs", account)
    if not cookies:
        return PublishResult(success=False, platform="xhs", error="Not logged in")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            await page.goto(CREATOR_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            if "login" in page.url.lower():
                return PublishResult(success=False, platform="xhs", error="Cookie expired")

            # Upload images or video
            if content.images:
                existing = [f for f in content.images if os.path.exists(f)]
                if existing:
                    file_input = page.locator('input[type="file"]').first
                    await file_input.set_input_files(existing)
                    await page.wait_for_timeout(3000)
            elif content.video:
                if os.path.exists(content.video):
                    file_input = page.locator('input[type="file"]').first
                    await file_input.set_input_files(content.video)
                    await page.wait_for_timeout(5000)

            # Fill title
            if content.title:
                try:
                    title_input = page.locator('[placeholder*="标题"], [class*="title"] input').first
                    await title_input.fill(content.title)
                except Exception:
                    pass

            # Fill content
            if content.text:
                try:
                    editor = page.locator('[contenteditable="true"], [class*="editor"]').first
                    await editor.click()
                    await page.keyboard.type(content.text)
                except Exception:
                    pass

            # Add tags
            for tag in content.tags[:5]:
                try:
                    await page.keyboard.type(f" #{tag}")
                    await page.wait_for_timeout(500)
                except Exception:
                    break

            await page.wait_for_timeout(1000)

            # Publish
            try:
                btn = page.locator('button:has-text("发布"), [class*="publish"] button').first
                await btn.click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                return PublishResult(success=False, platform="xhs", error=f"Publish button: {e}")

            return PublishResult(success=True, platform="xhs", url=page.url)

        except Exception as e:
            return PublishResult(success=False, platform="xhs", error=str(e))
        finally:
            await browser.close()
