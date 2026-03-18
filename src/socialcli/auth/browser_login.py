"""
Browser login — open browser for user to login, capture cookies.

Works for all platforms: user sees real login page, we capture cookies after login.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from socialcli.auth.cookie_store import save_cookies


def browser_login(
    platform: str,
    login_url: str,
    success_url_pattern: str = "",
    account: str = "default",
    headless: bool = False,
    timeout: int = 120,
) -> bool:
    """
    Open browser for login, wait for success, save cookies.

    Args:
        platform: Platform name (e.g. 'douyin')
        login_url: URL to open for login
        success_url_pattern: URL pattern indicating successful login
        account: Account name for cookie storage
        headless: Run in headless mode (usually False for login)
        timeout: Max wait time in seconds

    Returns:
        True if login successful
    """
    return asyncio.run(_browser_login_async(
        platform, login_url, success_url_pattern,
        account, headless, timeout,
    ))


async def _browser_login_async(
    platform: str,
    login_url: str,
    success_url_pattern: str,
    account: str,
    headless: bool,
    timeout: int,
) -> bool:
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = await context.new_page()

        try:
            await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)

            from rich.console import Console
            console = Console(stderr=True)
            console.print(f"\n[bold]Please login in the browser window...[/bold]")
            console.print(f"[dim]Waiting up to {timeout}s for login...[/dim]\n")

            # Wait for login success
            if success_url_pattern:
                try:
                    await page.wait_for_url(
                        f"**{success_url_pattern}**",
                        timeout=timeout * 1000,
                    )
                except Exception:
                    # Fallback: wait for any navigation away from login page
                    await page.wait_for_timeout(5000)
            else:
                # No pattern: wait for user to press Enter
                import sys
                console.print("[yellow]Press Enter after you've logged in...[/yellow]")
                await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)

            # Wait for JS to set all cookies (some platforms need extra time)
            await page.wait_for_timeout(3000)

            # Navigate to a logged-in page to ensure session cookies are set
            # (Reddit sets reddit_session only after visiting authenticated pages)
            try:
                if "reddit.com" in (success_url_pattern or login_url):
                    await page.goto("https://www.reddit.com/", wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(3000)
                elif "bilibili.com" in (success_url_pattern or login_url):
                    await page.goto("https://www.bilibili.com/", wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(2000)
            except Exception:
                pass  # Best effort — don't fail login if nav fails

            # Capture cookies
            cookies = await context.cookies()
            if not cookies:
                console.print("[red]No cookies captured. Login may have failed.[/red]")
                return False

            # Try to get user info from page
            nickname = ""
            user_id = ""
            try:
                nickname = await page.evaluate(
                    "document.querySelector('[class*=nickname], [class*=userName], [class*=user-name]')?.textContent?.trim() || ''"
                )
            except Exception:
                pass

            # Save cookies
            cookie_list = []
            for c in cookies:
                cookie_list.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ""),
                    "path": c.get("path", "/"),
                    "expires": c.get("expires", -1),
                    "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", False),
                    "sameSite": c.get("sameSite", "Lax"),
                })

            save_cookies(platform, cookie_list, account, nickname, user_id)
            console.print(f"[green]✔ Login successful! {len(cookie_list)} cookies saved.[/green]")
            return True

        except Exception as e:
            from rich.console import Console
            Console(stderr=True).print(f"[red]Login failed: {e}[/red]")
            return False
        finally:
            await browser.close()
