"""Адаптер Ozon — Playwright + Chromium (JS-рендеринг)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OzonParser:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.url = config["base_url"]
        self.selectors = config["selectors"]
        pag = config.get("pagination", {})
        self.max_pages = int(pag.get("max_pages", 3))
        self.next_btn_selector = pag.get("next_button_selector")
        self.scroll_passes = int(pag.get("scroll_passes", 4))

    def parse(self) -> list[dict]:
        # Импорт локальный, чтобы не требовать playwright при других режимах
        from playwright.sync_api import sync_playwright

        products: list[dict] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                locale="ru-RU",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(self.url, wait_until="domcontentloaded", timeout=60_000)

            for page_num in range(1, self.max_pages + 1):
                logger.info("Ozon: page %d", page_num)
                self._scroll(page)
                products.extend(self._collect_cards(page))

                if self.next_btn_selector and page.locator(self.next_btn_selector).count():
                    try:
                        page.locator(self.next_btn_selector).first.click(timeout=5_000)
                        page.wait_for_load_state("networkidle", timeout=20_000)
                    except Exception as exc:
                        logger.warning("Ozon: no more pages: %s", exc)
                        break
                else:
                    break

            browser.close()

        logger.info("Ozon: collected %d products", len(products))
        return products

    def _scroll(self, page) -> None:
        for _ in range(self.scroll_passes):
            page.mouse.wheel(0, 4_000)
            page.wait_for_timeout(800)

    def _collect_cards(self, page) -> list[dict]:
        cards = page.locator(self.selectors["card"])
        out: list[dict] = []
        for i in range(cards.count()):
            card = cards.nth(i)
            try:
                name = self._text(card, self.selectors.get("name"))
                brand = self._text(card, self.selectors.get("brand"))
                price_raw = self._text(card, self.selectors.get("price"))
                orig_raw = self._text(card, self.selectors.get("original_price"))
                link = self._attr(card, self.selectors.get("link"), "href")
                image = self._attr(card, self.selectors.get("image"), "src")
                out.append({
                    "id": None,
                    "name": name,
                    "brand": brand,
                    "price": _parse_price(price_raw),
                    "original_price": _parse_price(orig_raw),
                    "image": image,
                    "url": _absolute_url(link),
                    "availability": "in_stock",
                    "rating": None,
                    "reviews": None,
                })
            except Exception as exc:
                logger.debug("Ozon: card skipped: %s", exc)
        return out

    @staticmethod
    def _text(card, selector: str | None) -> str | None:
        if not selector:
            return None
        loc = card.locator(selector)
        return loc.first.inner_text().strip() if loc.count() else None

    @staticmethod
    def _attr(card, selector: str | None, attr: str) -> str | None:
        if not selector:
            return None
        loc = card.locator(selector)
        return loc.first.get_attribute(attr) if loc.count() else None


def _parse_price(raw: str | None) -> float | None:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit() or ch == ",")
    digits = digits.replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return None


def _absolute_url(href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith("http"):
        return href
    return f"https://www.ozon.ru{href}"
