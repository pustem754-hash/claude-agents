"""HTTP-клиент с обходом CloudFlare, ротацией UA и rate limiting."""
from __future__ import annotations

import logging
import random
import time
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


class Scraper:
    def __init__(
        self,
        delay_min: float = 6.0,
        delay_max: float = 12.0,
        timeout: int = 20,
        max_retries: int = 3,
    ) -> None:
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.timeout = timeout
        self.max_retries = max_retries
        self._cf_scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True}
        )
        self._session = requests.Session()

    def fetch(self, url: str, use_cloudflare: bool = False) -> str:
        client = self._cf_scraper if use_cloudflare else self._session
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "ru,en;q=0.8",
            }
            try:
                resp = client.get(url, headers=headers, timeout=self.timeout)
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

    def _sleep(self) -> None:
        time.sleep(random.uniform(self.delay_min, self.delay_max))
