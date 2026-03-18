"""Bilibili Playwright browser automation — publish videos."""
from __future__ import annotations

import asyncio
import os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"


def bilibili_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_publish_async(content, account))


async def _publish_async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright

    cookies = load_cookies("bilibili", account)
    if not cookies:
        return PublishResult(success=False, platform="bilibili", error="Not logged in")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            await page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            if "passport" in page.url.lower():
                return PublishResult(success=False, platform="bilibili", error="Cookie expired")

            # Upload video
            if not os.path.exists(content.video):
                return PublishResult(success=False, platform="bilibili", error=f"Video not found: {content.video}")

            file_input = page.locator('input[type="file"]').first
            await file_input.set_input_files(content.video)

            # Wait for upload
            try:
                await page.wait_for_selector(
                    '[class*="upload-success"], [class*="progress-100"], text=上传完成',
                    timeout=180000,
                )
            except Exception:
                await page.wait_for_timeout(20000)

            # Fill title
            if content.title:
                try:
                    title_input = page.locator(
                        'input[placeholder*="标题"], [class*="title-input"] input'
                    ).first
                    await title_input.clear()
                    await title_input.fill(content.title)
                except Exception:
                    pass

            # Fill description
            if content.text:
                try:
                    desc = page.locator(
                        '[class*="desc-container"] [contenteditable="true"], '
                        'textarea[placeholder*="简介"]'
                    ).first
                    await desc.click()
                    await page.keyboard.type(content.text)
                except Exception:
                    pass

            # Add tags
            for tag in content.tags[:5]:
                try:
                    tag_input = page.locator('[class*="tag-input"] input, input[placeholder*="标签"]').first
                    await tag_input.fill(tag)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(500)
                except Exception:
                    break

            await page.wait_for_timeout(1000)

            # Submit
            try:
                btn = page.locator('button:has-text("投稿"), [class*="submit-add"]').first
                await btn.click()
                await page.wait_for_timeout(5000)
            except Exception as e:
                return PublishResult(success=False, platform="bilibili", error=f"Submit button: {e}")

            return PublishResult(success=True, platform="bilibili", url=page.url)

        except Exception as e:
            return PublishResult(success=False, platform="bilibili", error=str(e))
        finally:
            await browser.close()
