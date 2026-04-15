"""Универсальный скрапер цен: Wildberries API + CSS-селекторы для известных сайтов."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

WB_ID_RE = re.compile(r"/catalog/(\d+)/")

# Специфичные CSS-селекторы для известных ru-магазинов
SITE_SELECTORS: dict[str, dict[str, str]] = {
    "ozon.ru": {
        "price": "[data-widget='webPrice'] span, span.tsHeadline500Medium",
        "name": "h1, [data-widget='webProductHeading'] h1",
    },
    "market.yandex.ru": {
        "price": "[data-auto='price-value'], span[data-auto='snippet-price-current']",
        "name": "h1[data-auto='productCardTitle'], h1",
    },
    "dns-shop.ru": {
        "price": ".product-buy__price",
        "name": "h1.product-card-top__title, h1",
    },
    "mvideo.ru": {
        "price": ".price__main-value",
        "name": "h1.product-title__text, h1",
    },
    "citilink.ru": {
        "price": ".ProductHeader-price-current, [data-meta-name='PriceBlock__price-value']",
        "name": "h1[data-meta-name='PageTitle'], h1",
    },
}


@dataclass
class Scraped:
    name: str
    price: Optional[float]


class PriceScraper:
    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru,en;q=0.8",
        })

    def get_price_and_name(self, url: str) -> Scraped:
        host = urlparse(url).netloc.lower().lstrip("www.")

        if "wildberries.ru" in host:
            result = self._wildberries(url)
            if result:
                return result

        html = self._fetch(url)
        soup = BeautifulSoup(html, "lxml")

        selectors = self._match_site(host)
        price: Optional[float] = None
        name: Optional[str] = None

        if selectors:
            name = self._text(soup, selectors.get("name"))
            price = _parse_price(self._text(soup, selectors.get("price")))

        # Универсальный fallback
        if not name:
            name = self._text(soup, "h1") or "Товар"
        if price is None:
            price = self._universal_price(soup)

        return Scraped(name=(name or "Товар").strip()[:200], price=price)

    def _fetch(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    def _wildberries(self, url: str) -> Optional[Scraped]:
        m = WB_ID_RE.search(url)
        if not m:
            return None
        pid = int(m.group(1))
        vol = pid // 100_000
        part = pid // 1_000

        # card.wb.ru достает базовую карточку
        for basket in range(1, 21):
            api = (
                f"https://basket-{basket:02d}.wbbasket.ru/"
                f"vol{vol}/part{part}/{pid}/info/ru/card.json"
            )
            try:
                resp = self.session.get(api, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    name = (
                        data.get("imt_name")
                        or data.get("subj_name")
                        or data.get("imt_new_attrs", [{}])[0].get("imt_name")
                        or "Товар WB"
                    )
                    break
            except Exception:
                continue
        else:
            name = "Товар WB"

        # Цена через search/detail API
        try:
            detail = self.session.get(
                "https://card.wb.ru/cards/v2/detail",
                params={"appType": 1, "curr": "rub", "dest": -1257786, "nm": pid},
                timeout=self.timeout,
            ).json()
            products = (detail.get("data") or {}).get("products") or []
            if products:
                sizes = products[0].get("sizes") or []
                price_u = None
                for s in sizes:
                    p = (s.get("price") or {}).get("product") or s.get("salePriceU")
                    if p:
                        price_u = p
                        break
                if price_u is None:
                    price_u = products[0].get("salePriceU") or products[0].get("priceU")
                price = round(int(price_u) / 100, 2) if price_u else None
                return Scraped(name=products[0].get("name") or name, price=price)
        except Exception as exc:
            logger.warning("WB detail API failed for %s: %s", pid, exc)

        return Scraped(name=name, price=None)

    @staticmethod
    def _match_site(host: str) -> Optional[dict[str, str]]:
        for domain, selectors in SITE_SELECTORS.items():
            if domain in host:
                return selectors
        return None

    @staticmethod
    def _text(soup: BeautifulSoup, selector: Optional[str]) -> Optional[str]:
        if not selector:
            return None
        for sel in selector.split(","):
            sel = sel.strip()
            if not sel:
                continue
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(" ", strip=True)
                if txt:
                    return txt
        return None

    @staticmethod
    def _universal_price(soup: BeautifulSoup) -> Optional[float]:
        # itemprop=price
        el = soup.select_one("[itemprop='price']")
        if el:
            val = el.get("content") or el.get_text(" ", strip=True)
            if val:
                price = _parse_price(val)
                if price:
                    return price
        # data-price
        el = soup.select_one("[data-price]")
        if el:
            price = _parse_price(el.get("data-price") or "")
            if price:
                return price
        # meta og:price:amount
        meta = soup.find("meta", attrs={"property": "product:price:amount"})
        if meta and meta.get("content"):
            return _parse_price(meta["content"])
        return None


def _parse_price(raw: str | None) -> Optional[float]:
    if not raw:
        return None
    digits = re.sub(r"[^\d,\.]", "", raw).replace(",", ".")
    if not digits:
        return None
    # если несколько точек — оставляем первую как целую/дробную
    if digits.count(".") > 1:
        first, *rest = digits.split(".")
        digits = first + "".join(rest[:-1]) + "." + rest[-1] if rest else first
    try:
        return round(float(digits), 2)
    except ValueError:
        return None
