"""Универсальный HTML-парсер по CSS-селекторам (BeautifulSoup + lxml)."""
from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HtmlCatalogParser:
    def __init__(self, config: dict[str, Any], fetcher) -> None:
        self.config = config
        self.fetcher = fetcher
        self.base_url = config["base_url"]
        self.selectors = config["selectors"]
        pag = config.get("pagination", {})
        self.max_pages = int(pag.get("max_pages", 3))
        self.pagination_type = pag.get("type", "next_button")
        self.next_selector = pag.get("next_selector")
        self.page_param = pag.get("page_param", "page")

    def parse(self) -> list[dict]:
        products: list[dict] = []
        current_url: Optional[str] = self.base_url

        for page_num in range(1, self.max_pages + 1):
            url = self._build_url(current_url, page_num)
            logger.info("HTML page %d: %s", page_num, url)
            try:
                html = self.fetcher.get(url).text
            except Exception as exc:
                logger.warning("Fetch failed on page %d: %s", page_num, exc)
                break

            soup = BeautifulSoup(html, "lxml")
            cards = soup.select(self.selectors["card"])
            if not cards:
                logger.info("No cards on page %d, stopping", page_num)
                break

            for card in cards:
                products.append(self._extract_card(card))

            if self.pagination_type == "next_button":
                current_url = self._find_next(soup, url)
                if not current_url:
                    logger.info("No next page link — stopping at page %d", page_num)
                    break

        logger.info("HTML: collected %d products", len(products))
        return products

    def _build_url(self, url: str, page_num: int) -> str:
        if self.pagination_type == "page_param" and page_num > 1:
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}{self.page_param}={page_num}"
        return url

    def _extract_card(self, card) -> dict:
        return {
            "id": self._text(card, self.selectors.get("id")),
            "name": self._text(card, self.selectors.get("name")),
            "brand": self._text(card, self.selectors.get("brand")),
            "price": _parse_price(self._text(card, self.selectors.get("price"))),
            "original_price": _parse_price(self._text(card, self.selectors.get("original_price"))),
            "image": self._attr(card, self.selectors.get("image"), "src"),
            "url": self._abs(self._attr(card, self.selectors.get("link"), "href")),
            "availability": self._text(card, self.selectors.get("availability")) or "in_stock",
            "rating": _safe_float(self._text(card, self.selectors.get("rating"))),
            "reviews": _safe_int(self._text(card, self.selectors.get("reviews"))),
        }

    def _find_next(self, soup, current_url: str) -> Optional[str]:
        if not self.next_selector:
            return None
        link = soup.select_one(self.next_selector)
        if not link or not link.get("href"):
            return None
        return urljoin(current_url, link["href"])

    @staticmethod
    def _text(card, selector: str | None) -> str | None:
        if not selector:
            return None
        el = card.select_one(selector)
        return el.get_text(strip=True) if el else None

    @staticmethod
    def _attr(card, selector: str | None, attr: str) -> str | None:
        if not selector:
            return None
        el = card.select_one(selector)
        return el.get(attr) if el else None

    def _abs(self, href: str | None) -> str | None:
        return urljoin(self.base_url, href) if href else None


def _parse_price(raw: str | None) -> float | None:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit() or ch in ",.")
    digits = digits.replace(" ", "").replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return None


def _safe_float(raw: str | None) -> float | None:
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def _safe_int(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else None
