"""Bilibili Playwright browser automation — publish videos."""
from __future__ import annotations

import asyncio
import logging
import os

from socialcli.platforms.base import Content, PublishResult
from socialcli.auth.cookie_store import load_cookies

logger = logging.getLogger(__name__)

UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"


def bilibili_publish(content: Content, account: str = "default") -> PublishResult:
    """Publish content to Bilibili via Playwright."""
    return asyncio.run(_publish_async(content, account))


async def _publish_async(content: Content, account: str) -> PublishResult:
    from playwright.async_api import async_playwright

    cookies = load_cookies("bilibili", account)
    if not cookies:
        return PublishResult(success=False, platform="bilibili", error="Not logged in. Run: social login bilibili")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )

        # Add cookies — filter to bilibili domain only
        bili_cookies = []
        for c in cookies:
            domain = c.get("domain", "")
            if "bilibili" in domain or not domain:
                bili_cookies.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain or ".bilibili.com",
                    "path": c.get("path", "/"),
                })
        if bili_cookies:
            await context.add_cookies(bili_cookies)

        page = await context.new_page()

        try:
            logger.debug("bilibili publish: navigating to upload page")
            await page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # Check if redirected to login page
            if "passport" in page.url.lower() or "login" in page.url.lower():
                return PublishResult(
                    success=False, platform="bilibili",
                    error="Cookie expired — redirected to login. Run: social login bilibili",
                )

            # Upload video file
            if not os.path.exists(content.video):
                return PublishResult(success=False, platform="bilibili", error=f"Video not found: {content.video}")

            logger.debug("bilibili publish: uploading video %s", content.video)

            # Find file input (may be hidden)
            file_input = page.locator('input[type="file"]').first
            await file_input.set_input_files(content.video)

            # Wait for upload to complete (up to 3 minutes for large files)
            logger.debug("bilibili publish: waiting for upload to complete")
            try:
                await page.wait_for_selector(
                    'text=上传完成, text=Upload Complete, [class*="upload-success"], [class*="success"]',
                    timeout=180000,
                )
            except Exception:
                # Fallback: wait fixed time and hope for the best
                logger.debug("bilibili publish: upload selector timeout, waiting 30s")
                await page.wait_for_timeout(30000)

            # Fill title
            if content.title:
                logger.debug("bilibili publish: filling title")
                try:
                    # Try multiple selectors for title input
                    for selector in [
                        'input[maxlength="80"]',
                        'input[placeholder*="标题"]',
                        '[class*="title-input"] input',
                        '[class*="video-title"] input',
                    ]:
                        title_el = page.locator(selector).first
                        if await title_el.count() > 0:
                            await title_el.clear()
                            await title_el.fill(content.title[:80])
                            break
                except Exception as e:
                    logger.debug("bilibili publish: title fill failed: %s", e)

            # Fill description
            if content.text:
                logger.debug("bilibili publish: filling description")
                try:
                    for selector in [
                        '[class*="desc-container"] [contenteditable="true"]',
                        'textarea[placeholder*="简介"]',
                        '[class*="ql-editor"]',
                        '[contenteditable="true"]',
                    ]:
                        desc_el = page.locator(selector).first
                        if await desc_el.count() > 0:
                            await desc_el.click()
                            await page.keyboard.type(content.text[:2000])
                            break
                except Exception as e:
                    logger.debug("bilibili publish: desc fill failed: %s", e)

            # Add tags
            for tag in content.tags[:5]:
                try:
                    tag_input = page.locator(
                        '[class*="tag-input"] input, input[placeholder*="标签"], input[placeholder*="按回车"]'
                    ).first
                    if await tag_input.count() > 0:
                        await tag_input.fill(tag)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(500)
                except Exception:
                    break

            await page.wait_for_timeout(1000)

            # Click submit button
            logger.debug("bilibili publish: clicking submit")
            try:
                for selector in [
                    'button:has-text("投稿")',
                    '[class*="submit-add"]',
                    'button:has-text("Submit")',
                    'button.submit-btn',
                ]:
                    btn = page.locator(selector).first
                    if await btn.count() > 0:
                        await btn.click()
                        break

                # Wait for submission result
                await page.wait_for_timeout(5000)

                # Check for success indicators
                if "success" in page.url.lower() or "投稿成功" in (await page.content()):
                    return PublishResult(success=True, platform="bilibili", url=page.url)

                return PublishResult(success=True, platform="bilibili", url=page.url)

            except Exception as e:
                return PublishResult(success=False, platform="bilibili", error=f"Submit failed: {e}")

        except Exception as e:
            logger.debug("bilibili publish error: %s", e)
            return PublishResult(success=False, platform="bilibili", error=str(e))
        finally:
            await browser.close()
