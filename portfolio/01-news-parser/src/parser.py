"""XPath-парсер статей с YAML-конфигурацией селекторов."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from dateutil import parser as date_parser
from lxml import html as lxml_html

from .models import Article

logger = logging.getLogger(__name__)


class ArticleParser:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        with self.config_path.open("r", encoding="utf-8") as f:
            self.config: dict[str, Any] = yaml.safe_load(f) or {}

    def site_uses_cloudflare(self, site_key: str) -> bool:
        return bool(self.config.get(site_key, {}).get("cloudflare", False))

    def parse(self, html: str, url: str, site_key: str) -> Article:
        if site_key not in self.config:
            raise KeyError(f"Site '{site_key}' not configured in {self.config_path}")

        tree = lxml_html.fromstring(html)
        selectors = self.config[site_key]["selectors"]

        title = self._extract(tree, selectors.get("title", []))
        text_nodes = self._extract_many(tree, selectors.get("text", []))
        text = "\n\n".join(t.strip() for t in text_nodes if t and t.strip())
        author = self._extract(tree, selectors.get("author", []))
        raw_date = self._extract(tree, selectors.get("date", []))
        published_at = self._normalize_date(raw_date) if raw_date else None

        return Article(
            url=url,
            site_key=site_key,
            title=(title or "").strip(),
            text=text.strip(),
            author=(author or "").strip() or None,
            published_at=published_at,
        )

    def _extract(self, tree, xpath_list: list[str]) -> str | None:
        for xp in xpath_list:
            try:
                result = tree.xpath(xp)
            except Exception as exc:
                logger.debug("XPath error for %s: %s", xp, exc)
                continue
            if not result:
                continue
            first = result[0]
            value = first if isinstance(first, str) else (first.text_content() or "")
            value = value.strip()
            if value:
                return value
        return None

    def _extract_many(self, tree, xpath_list: list[str]) -> list[str]:
        for xp in xpath_list:
            try:
                nodes = tree.xpath(xp)
            except Exception:
                continue
            if nodes:
                return [n if isinstance(n, str) else n.text_content() for n in nodes]
        return []

    @staticmethod
    def _normalize_date(raw: str) -> str | None:
        try:
            return date_parser.parse(raw).isoformat()
        except (ValueError, TypeError):
            return raw or None
