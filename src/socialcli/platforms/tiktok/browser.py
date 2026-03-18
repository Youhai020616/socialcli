"""TikTok Playwright browser automation — publish videos."""
from __future__ import annotations

import asyncio
import os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

UPLOAD_URL = "https://www.tiktok.com/creator#/upload?scene=creator_center"


def tiktok_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_publish_async(content, account))


async def _publish_async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright

    cookies = load_cookies("tiktok", account)
    if not cookies:
        return PublishResult(success=False, platform="tiktok", error="Not logged in")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            await page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            if "login" in page.url.lower():
                return PublishResult(success=False, platform="tiktok", error="Cookie expired")

            # Upload video
            if not os.path.exists(content.video):
                return PublishResult(success=False, platform="tiktok", error=f"Video not found: {content.video}")

            file_input = page.locator('input[type="file"]').first
            await file_input.set_input_files(content.video)
            await page.wait_for_timeout(5000)

            # Wait for upload
            try:
                await page.wait_for_selector(
                    '[class*="upload-success"], [class*="progress-100"]',
                    timeout=120000,
                )
            except Exception:
                await page.wait_for_timeout(15000)

            # Fill caption
            caption = content.text or content.title or ""
            if caption:
                try:
                    editor = page.locator('[contenteditable="true"], [data-text="true"]').first
                    await editor.click()
                    await page.keyboard.type(caption)
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

            # Click post button
            try:
                btn = page.locator('button:has-text("Post"), [data-e2e="post-button"]').first
                await btn.click()
                await page.wait_for_timeout(5000)
            except Exception as e:
                return PublishResult(success=False, platform="tiktok", error=f"Post button: {e}")

            return PublishResult(success=True, platform="tiktok", url=page.url)

        except Exception as e:
            return PublishResult(success=False, platform="tiktok", error=str(e))
        finally:
            await browser.close()
