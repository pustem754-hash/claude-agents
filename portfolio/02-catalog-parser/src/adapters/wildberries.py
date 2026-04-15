"""Адаптер Wildberries — публичный Search API."""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v5/search"


class WildberriesParser:
    def __init__(self, config: dict[str, Any], fetcher) -> None:
        self.config = config
        self.fetcher = fetcher
        self.max_pages = int(config.get("pagination", {}).get("max_pages", 3))
        self.default_query = config.get("default_query", "ноутбук")

    def parse(self, query: Optional[str] = None) -> list[dict]:
        q = query or self.default_query
        products: list[dict] = []

        for page in range(1, self.max_pages + 1):
            params = {
                "ab_testing": "false",
                "appType": 1,
                "curr": "rub",
                "dest": -1257786,
                "page": page,
                "query": q,
                "resultset": "catalog",
                "sort": "popular",
                "spp": 30,
                "suppressSpellcheck": "false",
            }
            logger.info("WB search page=%d query=%r", page, q)
            try:
                payload = self.fetcher.get_json(SEARCH_URL, params=params)
            except Exception as exc:
                logger.warning("WB API error on page %d: %s", page, exc)
                break

            items = (payload.get("data") or {}).get("products") or []
            if not items:
                logger.info("WB: no more products, stopping at page %d", page)
                break

            for it in items:
                products.append(self._normalize(it))

        logger.info("WB: collected %d products", len(products))
        return products

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict:
        pid = raw.get("id")
        # Цены на WB приходят в копейках
        price = _kopeks_to_rub(raw.get("salePriceU") or raw.get("priceU"))
        original = _kopeks_to_rub(raw.get("priceU"))
        # Изображение по ID (WB CDN)
        image = _wb_image(pid) if pid else None
        return {
            "id": pid,
            "name": raw.get("name"),
            "brand": raw.get("brand"),
            "price": price,
            "original_price": original,
            "image": image,
            "url": f"https://www.wildberries.ru/catalog/{pid}/detail.aspx" if pid else None,
            "availability": "in_stock" if (raw.get("totalQuantity") or 0) > 0 else "out_of_stock",
            "rating": raw.get("reviewRating") or raw.get("rating"),
            "reviews": raw.get("feedbacks"),
        }


def _kopeks_to_rub(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(int(value) / 100, 2)
    except (TypeError, ValueError):
        return None


def _wb_image(pid: int) -> str:
    # Простая эвристика для CDN WB (basket-XX); реальный код обычно делает probe
    vol = pid // 100_000
    part = pid // 1_000
    basket = min(max(vol // 144 + 1, 1), 20)
    return f"https://basket-{basket:02d}.wbbasket.ru/vol{vol}/part{part}/{pid}/images/big/1.webp"
