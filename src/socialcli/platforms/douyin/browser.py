"""
Douyin Playwright browser automation — publish videos/images.

Replicates dy-cli's playwright_client publish flow.
"""
from __future__ import annotations

import asyncio
import os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies


CREATOR_URL = "https://creator.douyin.com/creator-micro/content/upload"


def douyin_publish(content: Content, account: str = "default") -> PublishResult:
    """Publish content to Douyin via Playwright."""
    return asyncio.run(_publish_async(content, account))


async def _publish_async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright

    cookies = load_cookies("douyin", account)
    if not cookies:
        return PublishResult(success=False, platform="douyin", error="Not logged in")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
        )

        # Inject cookies
        await context.add_cookies(cookies)

        page = await context.new_page()

        try:
            await page.goto(CREATOR_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # Check if login is valid
            if "login" in page.url.lower():
                return PublishResult(success=False, platform="douyin", error="Cookie expired, please re-login")

            # Upload media
            if content.video:
                if not os.path.exists(content.video):
                    return PublishResult(success=False, platform="douyin", error=f"Video not found: {content.video}")

                # Find upload input
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(content.video)
                await page.wait_for_timeout(3000)

                # Wait for upload to complete
                try:
                    await page.wait_for_selector(
                        '[class*="progress-100"], [class*="upload-success"], [class*="success"]',
                        timeout=120000,
                    )
                except Exception:
                    await page.wait_for_timeout(10000)  # Fallback wait

            elif content.images:
                # Switch to image mode if available
                try:
                    image_tab = page.locator('text=发布图文').first
                    await image_tab.click()
                    await page.wait_for_timeout(1000)
                except Exception:
                    pass

                file_input = page.locator('input[type="file"]').first
                existing_files = [f for f in content.images if os.path.exists(f)]
                if existing_files:
                    await file_input.set_input_files(existing_files)
                    await page.wait_for_timeout(3000)

            # Fill title
            if content.title:
                try:
                    title_input = page.locator('[class*="title"] input, [placeholder*="标题"]').first
                    await title_input.fill(content.title)
                except Exception:
                    pass

            # Fill description
            if content.text:
                try:
                    desc_editor = page.locator('[class*="editor"], [class*="description"], [contenteditable="true"]').first
                    await desc_editor.click()
                    await page.keyboard.type(content.text)
                except Exception:
                    pass

            # Add tags
            for tag in content.tags[:5]:
                try:
                    await page.keyboard.type(f" #{tag}")
                except Exception:
                    break

            await page.wait_for_timeout(1000)

            # Click publish button
            try:
                publish_btn = page.locator('button:has-text("发布"), [class*="publish"] button').first
                await publish_btn.click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                return PublishResult(success=False, platform="douyin", error=f"Publish button not found: {e}")

            return PublishResult(
                success=True,
                platform="douyin",
                url=page.url,
            )

        except Exception as e:
            return PublishResult(success=False, platform="douyin", error=str(e))
        finally:
            await browser.close()
