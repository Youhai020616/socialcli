"""Instagram Playwright — publish posts/reels."""
from __future__ import annotations
import asyncio, os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

def instagram_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_async(content, account))

async def _async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright
    cookies = load_cookies("instagram", account)
    if not cookies: return PublishResult(success=False, platform="instagram", error="Not logged in")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        try:
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            if "login" in page.url: return PublishResult(success=False, platform="instagram", error="Cookie expired")
            # Click create / new post button
            try:
                create_btn = page.locator('[aria-label="New post"], [aria-label="创建"], svg[aria-label*="New"]').first
                await create_btn.click(); await page.wait_for_timeout(2000)
            except Exception as e: return PublishResult(success=False, platform="instagram", error=f"Create button: {e}")
            # Upload media
            media = content.images[0] if content.images else content.video
            if not media or not os.path.exists(media):
                return PublishResult(success=False, platform="instagram", error="No media file found")
            fi = page.locator('input[type="file"]').first
            await fi.set_input_files(media); await page.wait_for_timeout(3000)
            # Click Next (crop) → Next (filter) → caption
            for _ in range(2):
                try:
                    nxt = page.locator('button:has-text("Next"), [aria-label="Next"]').first
                    await nxt.click(); await page.wait_for_timeout(1500)
                except Exception: break
            # Add caption
            if content.text:
                try:
                    caption = page.locator('[aria-label*="caption"], [aria-label*="说明"], textarea').first
                    await caption.click(); await page.keyboard.type(content.text)
                except Exception: pass
            # Share
            try:
                share = page.locator('button:has-text("Share"), button:has-text("分享")').first
                await share.click(); await page.wait_for_timeout(5000)
            except Exception as e: return PublishResult(success=False, platform="instagram", error=f"Share: {e}")
            return PublishResult(success=True, platform="instagram", url=page.url)
        except Exception as e: return PublishResult(success=False, platform="instagram", error=str(e))
        finally: await browser.close()
