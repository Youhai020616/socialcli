"""Weibo Playwright browser automation — publish posts."""
from __future__ import annotations

import asyncio
import os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies


def weibo_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_publish_async(content, account))


async def _publish_async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright

    cookies = load_cookies("weibo", account)
    if not cookies:
        return PublishResult(success=False, platform="weibo", error="Not logged in")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            await page.goto("https://weibo.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            if "login" in page.url.lower() or "passport" in page.url.lower():
                return PublishResult(success=False, platform="weibo", error="Cookie expired")

            # Click compose area
            try:
                editor = page.locator(
                    '[class*="Form_input"], textarea[placeholder*="说"], '
                    '[contenteditable="true"]'
                ).first
                await editor.click()
                await page.wait_for_timeout(1000)
                await page.keyboard.type(content.text or content.title or "")
            except Exception as e:
                return PublishResult(success=False, platform="weibo", error=f"Editor: {e}")

            # Upload images
            if content.images:
                try:
                    file_input = page.locator('input[type="file"]').first
                    existing = [f for f in content.images if os.path.exists(f)]
                    if existing:
                        await file_input.set_input_files(existing)
                        await page.wait_for_timeout(3000)
                except Exception:
                    pass

            await page.wait_for_timeout(1000)

            # Click publish
            try:
                btn = page.locator(
                    'button:has-text("发博"), button:has-text("发送"), '
                    '[class*="Form_btn"], [node-type="submit"]'
                ).first
                await btn.click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                return PublishResult(success=False, platform="weibo", error=f"Submit: {e}")

            return PublishResult(success=True, platform="weibo", url=page.url)

        except Exception as e:
            return PublishResult(success=False, platform="weibo", error=str(e))
        finally:
            await browser.close()
