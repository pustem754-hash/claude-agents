"""HTTP-клиент: cloudscraper, requests, headless Chromium + stealth, FlareSolverr, proxy."""
from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Optional

import cloudscraper
import requests

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

PLAYWRIGHT_UA = USER_AGENTS[0]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = { runtime: {} };
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);
"""


def _proxy_to_playwright(proxy_url: str) -> dict:
    """Конвертирует 'http://user:pass@host:port' в формат Playwright-context."""
    from urllib.parse import urlparse
    parsed = urlparse(proxy_url)
    server = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        server += f":{parsed.port}"
    result = {"server": server}
    if parsed.username:
        result["username"] = parsed.username
    if parsed.password:
        result["password"] = parsed.password
    return result


class Scraper:
    def __init__(
        self,
        delay_min: float = 6.0,
        delay_max: float = 12.0,
        timeout: int = 20,
        max_retries: int = 3,
        playwright_timeout: int = 30_000,
        playwright_viewport: tuple[int, int] = (1920, 1080),
        storage_state_dir: str | Path = ".playwright_state",
        flaresolverr_url: Optional[str] = None,
    ) -> None:
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.timeout = timeout
        self.max_retries = max_retries
        self.playwright_timeout = playwright_timeout
        self.playwright_viewport = playwright_viewport
        self.storage_state_dir = Path(storage_state_dir)
        self.flaresolverr_url = flaresolverr_url or os.getenv("FLARESOLVERR_URL")

        self._cf_scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True}
        )
        self._session = requests.Session()

    # ------------------------------------------------------------------- public
    def fetch(
        self,
        url: str,
        use_cloudflare: bool = False,
        use_playwright: bool = False,
        use_flaresolverr: bool = False,
        use_stealth: bool = False,
        site_key: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> str:
        """Возвращает HTML страницы. Стратегия выбирается флагами.

        Приоритет флагов: use_flaresolverr > use_playwright > use_cloudflare.
        use_stealth применяется только совместно с use_playwright.
        """
        proxy = proxy or os.getenv("HTTP_PROXY")
        if use_flaresolverr:
            return self.fetch_with_flaresolverr(url, proxy=proxy)
        if use_playwright:
            return self.fetch_with_playwright(
                url, site_key=site_key, proxy=proxy, use_stealth=use_stealth,
            )
        return self._fetch_http(url, use_cloudflare=use_cloudflare, proxy=proxy)

    def fetch_with_playwright(
        self,
        url: str,
        site_key: Optional[str] = None,
        proxy: Optional[str] = None,
        use_stealth: bool = False,
    ) -> str:
        """Публично: headless Chromium + storage_state.

        use_stealth=True включает tf-playwright-stealth. ВНИМАНИЕ: он может ломать
        загрузку на некоторых anti-bot системах (замечено на rbc.ru — сервер
        отдаёт 39-байтную заглушку). Включайте только для сайтов, где точно помогает
        (например, tass.ru с RU-прокси).
        """
        return self._fetch_playwright(url, site_key=site_key, proxy=proxy, use_stealth=use_stealth)

    def fetch_with_flaresolverr(self, url: str, proxy: Optional[str] = None) -> str:
        """Публично: проксирует запрос через FlareSolverr (Docker-сервис)."""
        return self._fetch_flaresolverr(url, proxy=proxy)

    # ------------------------------------------------------------------- http
    def _fetch_http(
        self,
        url: str,
        use_cloudflare: bool,
        proxy: Optional[str] = None,
    ) -> str:
        client = self._cf_scraper if use_cloudflare else self._session
        proxies = {"http": proxy, "https": proxy} if proxy else None
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "ru,en;q=0.8",
            }
            try:
                resp = client.get(url, headers=headers, timeout=self.timeout, proxies=proxies)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding or "utf-8"
                    self._sleep()
                    return resp.text

                if resp.status_code in (403, 429, 503) and attempt < self.max_retries:
                    backoff = (2 ** attempt) + random.random()
                    logger.warning(
                        "Got %s for %s — retrying in %.1fs (attempt %d/%d)",
                        resp.status_code, url, backoff, attempt, self.max_retries,
                    )
                    time.sleep(backoff)
                    continue

                raise requests.HTTPError(f"HTTP {resp.status_code} on {url}", response=resp)

            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    backoff = (2 ** attempt) + random.random()
                    logger.warning("Network error on %s — retry in %.1fs: %s", url, backoff, exc)
                    time.sleep(backoff)
                    continue
                raise

        raise RuntimeError(f"Unreachable retry branch for {url}: {last_exc}")

    # ------------------------------------------------------------------- playwright
    def _fetch_playwright(
        self,
        url: str,
        site_key: Optional[str] = None,
        proxy: Optional[str] = None,
        use_stealth: bool = False,
    ) -> str:
        """Headless Chromium + storage_state. Опциональный tf-playwright-stealth."""
        from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

        stealth_sync = None
        have_stealth = False
        if use_stealth:
            try:
                from playwright_stealth import stealth_sync as _stealth
                stealth_sync = _stealth
                have_stealth = True
            except ImportError:
                logger.warning("playwright_stealth requested but not installed — skipping")

        width, height = self.playwright_viewport
        state_file: Optional[Path] = None
        if site_key:
            self.storage_state_dir.mkdir(parents=True, exist_ok=True)
            state_file = self.storage_state_dir / f"{site_key}.json"

        proxy_config = _proxy_to_playwright(proxy) if proxy else None
        logger.info(
            "Playwright fetch: %s (viewport %dx%d, stealth=%s, storage_state=%s, proxy=%s)",
            url, width, height, have_stealth,
            state_file.name if state_file and state_file.exists() else "new",
            "yes" if proxy_config else "no",
        )

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                proxy=proxy_config,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            context_kwargs = dict(
                viewport={"width": width, "height": height},
                user_agent=PLAYWRIGHT_UA,
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"},
            )
            if state_file and state_file.exists():
                context_kwargs["storage_state"] = str(state_file)

            context = browser.new_context(**context_kwargs)
            context.add_init_script(STEALTH_INIT_SCRIPT)
            page = context.new_page()
            if have_stealth:
                try:
                    stealth_sync(page)
                except Exception as exc:
                    logger.warning("stealth_sync failed, continuing without it: %s", exc)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.playwright_timeout)
                try:
                    page.wait_for_load_state("networkidle", timeout=self.playwright_timeout)
                except PWTimeout:
                    logger.warning("networkidle timeout for %s — continuing with current DOM", url)

                # Рандомная пауза (эмуляция чтения пользователем)
                page.wait_for_timeout(random.randint(1500, 3500))
                html = page.content()

                if state_file:
                    try:
                        context.storage_state(path=str(state_file))
                        logger.debug("Saved storage_state to %s", state_file)
                    except Exception as exc:
                        logger.debug("Failed to save storage_state: %s", exc)

                self._sleep()
                return html
            finally:
                context.close()
                browser.close()

    # ------------------------------------------------------------------- flaresolverr
    def _fetch_flaresolverr(self, url: str, proxy: Optional[str] = None) -> str:
        """Проксирует запрос через FlareSolverr (http://host:8191/v1)."""
        endpoint = (self.flaresolverr_url or "http://localhost:8191").rstrip("/") + "/v1"

        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": self.playwright_timeout,
        }
        if proxy:
            payload["proxy"] = {"url": proxy}

        logger.info("FlareSolverr fetch: %s via %s", url, endpoint)
        resp = requests.post(endpoint, json=payload, timeout=self.playwright_timeout / 1000 + 10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            raise RuntimeError(f"FlareSolverr error: {data.get('message', data)}")

        solution = data.get("solution") or {}
        html = solution.get("response")
        if not html:
            raise RuntimeError(f"FlareSolverr returned empty response: {solution}")

        self._sleep()
        return html

    # ------------------------------------------------------------------- helpers
    def _sleep(self) -> None:
        time.sleep(random.uniform(self.delay_min, self.delay_max))
