"""Facebook Playwright — publish posts."""
from __future__ import annotations
import asyncio, os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

def facebook_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_async(content, account))

async def _async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright
    cookies = load_cookies("facebook", account)
    if not cookies: return PublishResult(success=False, platform="facebook", error="Not logged in")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        try:
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            if "login" in page.url: return PublishResult(success=False, platform="facebook", error="Cookie expired")
            # Click "What's on your mind?"
            try:
                box = page.locator('[aria-label*="on your mind"], [aria-label*="想说"], [role="button"]:has-text("What")').first
                await box.click(); await page.wait_for_timeout(2000)
            except Exception as e: return PublishResult(success=False, platform="facebook", error=f"Composer: {e}")
            # Type
            try:
                editor = page.locator('[contenteditable="true"][role="textbox"]').first
                await editor.click(); await page.keyboard.type(content.text or content.title or "")
            except Exception: pass
            # Upload images
            if content.images:
                try:
                    fi = page.locator('input[type="file"][accept*="image"]').first
                    existing = [f for f in content.images if os.path.exists(f)]
                    if existing: await fi.set_input_files(existing); await page.wait_for_timeout(3000)
                except Exception: pass
            await page.wait_for_timeout(1000)
            try:
                btn = page.locator('div[aria-label="Post"], button:has-text("Post")').first
                await btn.click(); await page.wait_for_timeout(3000)
            except Exception as e: return PublishResult(success=False, platform="facebook", error=f"Post: {e}")
            return PublishResult(success=True, platform="facebook", url=page.url)
        except Exception as e: return PublishResult(success=False, platform="facebook", error=str(e))
        finally: await browser.close()
