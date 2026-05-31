"""
Test: can we fetch a tass.ru article through playwright-stealth?
Prints status, title, first 500 chars of body text, or blocked marker.
"""
import asyncio
import sys
from playwright.async_api import async_playwright

try:
    from playwright_stealth import Stealth
    HAS_STEALTH_V2 = True
except ImportError:
    HAS_STEALTH_V2 = False
    try:
        from playwright_stealth import stealth_async
    except ImportError:
        print("playwright-stealth not installed", flush=True)
        sys.exit(1)


URL = "https://tass.ru/proisshestviya/27109033"


async def run():
    async with async_playwright() as p:
        if HAS_STEALTH_V2:
            stealth = Stealth()
            browser = await p.chromium.launch(headless=True, args=[
                "--disable-blink-features=AutomationControlled",
            ])
            context = await browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"),
                locale="ru-RU",
                viewport={"width": 1366, "height": 768},
            )
            await stealth.apply_stealth_async(context)
            page = await context.new_page()
        else:
            browser = await p.chromium.launch(headless=True, args=[
                "--disable-blink-features=AutomationControlled",
            ])
            context = await browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"),
                locale="ru-RU",
                viewport={"width": 1366, "height": 768},
            )
            page = await context.new_page()
            await stealth_async(page)

        print(f"[INFO] Navigating {URL}", flush=True)
        try:
            resp = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"[ERROR] goto failed: {e}", flush=True)
            await browser.close()
            return

        status = resp.status if resp else None
        print(f"[INFO] HTTP status: {status}", flush=True)

        try:
            await page.wait_for_timeout(3000)
        except Exception:
            pass

        html = await page.content()
        title = await page.title()
        print(f"[INFO] Title: {title!r}", flush=True)
        print(f"[INFO] HTML length: {len(html)}", flush=True)

        markers = [
            "servicepipe", "ServicePipe", "Проверка безопасности",
            "Checking your browser", "captcha", "challenge-platform",
            "Access denied", "403 Forbidden",
        ]
        for m in markers:
            if m.lower() in html.lower():
                print(f"[BLOCKED] marker found: {m}", flush=True)

        try:
            body_text = await page.inner_text("article")
        except Exception:
            body_text = await page.inner_text("body")

        body_text = body_text.strip()
        print("[INFO] Body text (first 800 chars):", flush=True)
        print(body_text[:800], flush=True)
        print("---END---", flush=True)

        await browser.close()


asyncio.run(run())
