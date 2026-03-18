"""LinkedIn Playwright browser automation — publish posts."""
from __future__ import annotations

import asyncio
import os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

FEED_URL = "https://www.linkedin.com/feed/"


def linkedin_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_publish_async(content, account))


async def _publish_async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright

    cookies = load_cookies("linkedin", account)
    if not cookies:
        return PublishResult(success=False, platform="linkedin", error="Not logged in")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            await page.goto(FEED_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            if "login" in page.url.lower() or "checkpoint" in page.url.lower():
                return PublishResult(success=False, platform="linkedin", error="Cookie expired")

            # Click "Start a post" button
            try:
                start_btn = page.locator(
                    'button:has-text("Start a post"), '
                    '[class*="share-box-feed-entry__trigger"], '
                    '[data-control-name="share.ShareBoxFeature"]'
                ).first
                await start_btn.click()
                await page.wait_for_timeout(2000)
            except Exception as e:
                return PublishResult(success=False, platform="linkedin", error=f"Cannot open post editor: {e}")

            # Type content in editor
            post_text = content.text or content.title or ""
            if post_text:
                try:
                    editor = page.locator(
                        '[contenteditable="true"], '
                        '[role="textbox"], '
                        '.ql-editor'
                    ).first
                    await editor.click()
                    await page.keyboard.type(post_text)
                except Exception:
                    pass

            await page.wait_for_timeout(1000)

            # Upload images if any
            if content.images:
                try:
                    # Click media button
                    media_btn = page.locator(
                        'button[aria-label*="photo"], button[aria-label*="image"], '
                        '[data-control-name="share.addPhoto"]'
                    ).first
                    await media_btn.click()
                    await page.wait_for_timeout(1000)

                    existing = [f for f in content.images if os.path.exists(f)]
                    if existing:
                        file_input = page.locator('input[type="file"]').first
                        await file_input.set_input_files(existing)
                        await page.wait_for_timeout(3000)
                except Exception:
                    pass

            # Click Post button
            try:
                post_btn = page.locator(
                    'button:has-text("Post"), '
                    '[class*="share-actions__primary-action"]'
                ).first
                await post_btn.click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                return PublishResult(success=False, platform="linkedin", error=f"Post button: {e}")

            return PublishResult(success=True, platform="linkedin", url=page.url)

        except Exception as e:
            return PublishResult(success=False, platform="linkedin", error=str(e))
        finally:
            await browser.close()
