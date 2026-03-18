"""Threads Playwright — publish posts."""
from __future__ import annotations
import asyncio, os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

def threads_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_async(content, account))

async def _async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright
    cookies = load_cookies("threads", account)
    if not cookies: return PublishResult(success=False, platform="threads", error="Not logged in")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        try:
            await page.goto("https://www.threads.net/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            if "login" in page.url: return PublishResult(success=False, platform="threads", error="Cookie expired")
            # Click compose
            try:
                compose = page.locator('[aria-label*="Create"], [aria-label*="new thread"], [data-pressable-container="true"]').first
                await compose.click(); await page.wait_for_timeout(2000)
            except Exception as e: return PublishResult(success=False, platform="threads", error=f"Compose: {e}")
            # Type
            try:
                editor = page.locator('[contenteditable="true"], [role="textbox"]').first
                await editor.click(); await page.keyboard.type(content.text or content.title or "")
            except Exception: pass
            # Upload image
            if content.images:
                try:
                    fi = page.locator('input[type="file"]').first
                    existing = [f for f in content.images if os.path.exists(f)]
                    if existing: await fi.set_input_files(existing[0]); await page.wait_for_timeout(3000)
                except Exception: pass
            try:
                btn = page.locator('div[role="button"]:has-text("Post"), button:has-text("Post")').first
                await btn.click(); await page.wait_for_timeout(3000)
            except Exception as e: return PublishResult(success=False, platform="threads", error=f"Post: {e}")
            return PublishResult(success=True, platform="threads", url=page.url)
        except Exception as e: return PublishResult(success=False, platform="threads", error=str(e))
        finally: await browser.close()
