"""HTTP-клиент с retry, экспоненциальным backoff, ротацией UA и rate limiting."""
from __future__ import annotations

import logging
import os
import random
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


class HttpFetcher:
    def __init__(
        self,
        delay_min: float = 1.0,
        delay_max: float = 3.0,
        timeout: int = 20,
        max_retries: int = 3,
    ) -> None:
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.timeout = timeout

        retries = Retry(
            total=max_retries,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
        )
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        proxy = os.getenv("HTTP_PROXY")
        if proxy:
            self.session.proxies.update({"http": proxy, "https": proxy})

    def get(self, url: str, params: Optional[dict] = None) -> requests.Response:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "ru,en;q=0.8",
        }
        resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        self._sleep()
        return resp

    def get_json(self, url: str, params: Optional[dict] = None) -> dict:
        return self.get(url, params=params).json()

    def _sleep(self) -> None:
        time.sleep(random.uniform(self.delay_min, self.delay_max))
