"""Kuaishou Playwright browser automation — publish videos."""
from __future__ import annotations
import asyncio, os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

def kuaishou_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_publish_async(content, account))

async def _publish_async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright
    cookies = load_cookies("kuaishou", account)
    if not cookies:
        return PublishResult(success=False, platform="kuaishou", error="Not logged in")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.add_cookies(cookies)
        page = await context.new_page()
        try:
            await page.goto("https://cp.kuaishou.com/article/publish/video", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            if "login" in page.url.lower() or "passport" in page.url.lower():
                return PublishResult(success=False, platform="kuaishou", error="Cookie expired")

            if not os.path.exists(content.video):
                return PublishResult(success=False, platform="kuaishou", error=f"Video not found: {content.video}")

            file_input = page.locator('input[type="file"]').first
            await file_input.set_input_files(content.video)
            await page.wait_for_timeout(10000)

            if content.title or content.text:
                try:
                    editor = page.locator('[contenteditable="true"], textarea').first
                    await editor.click()
                    await page.keyboard.type(content.title or content.text)
                except Exception:
                    pass

            try:
                btn = page.locator('button:has-text("发布"), [class*="publish"]').first
                await btn.click()
                await page.wait_for_timeout(5000)
            except Exception as e:
                return PublishResult(success=False, platform="kuaishou", error=f"Submit: {e}")

            return PublishResult(success=True, platform="kuaishou", url=page.url)
        except Exception as e:
            return PublishResult(success=False, platform="kuaishou", error=str(e))
        finally:
            await browser.close()
