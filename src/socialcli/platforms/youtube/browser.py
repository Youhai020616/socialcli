"""YouTube Playwright — upload video via studio.youtube.com."""
from __future__ import annotations
import asyncio, os
from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

def youtube_publish(content: Content, account: str = "default") -> PublishResult:
    return asyncio.run(_async(content, account))

async def _async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright
    cookies = load_cookies("youtube", account)
    if not cookies: return PublishResult(success=False, platform="youtube", error="Not logged in")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        try:
            await page.goto("https://studio.youtube.com/channel/UC/videos/upload?d=ud", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            if "accounts.google" in page.url: return PublishResult(success=False, platform="youtube", error="Cookie expired")
            if not os.path.exists(content.video): return PublishResult(success=False, platform="youtube", error=f"Not found: {content.video}")
            fi = page.locator('input[type="file"]').first
            await fi.set_input_files(content.video)
            await page.wait_for_timeout(5000)
            if content.title:
                try:
                    ti = page.locator('[id="textbox"]').first
                    await ti.click(); await ti.fill(""); await page.keyboard.type(content.title)
                except Exception: pass
            if content.text:
                try:
                    desc = page.locator('[id="textbox"]').nth(1)
                    await desc.click(); await page.keyboard.type(content.text)
                except Exception: pass
            # Click through Next buttons
            for _ in range(3):
                try:
                    nxt = page.locator('button:has-text("Next"), #next-button').first
                    await nxt.click(); await page.wait_for_timeout(1000)
                except Exception: break
            # Select Public visibility
            try: await page.locator('[name="PUBLIC"]').click()
            except Exception: pass
            # Click Done/Publish
            try:
                done = page.locator('button:has-text("Publish"), button:has-text("Done"), #done-button').first
                await done.click(); await page.wait_for_timeout(5000)
            except Exception as e: return PublishResult(success=False, platform="youtube", error=f"Publish: {e}")
            return PublishResult(success=True, platform="youtube", url=page.url)
        except Exception as e: return PublishResult(success=False, platform="youtube", error=str(e))
        finally: await browser.close()
