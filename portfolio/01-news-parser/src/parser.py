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

    def site_uses_playwright(self, site_key: str) -> bool:
        return bool(self.config.get(site_key, {}).get("use_playwright", False))

    def site_uses_flaresolverr(self, site_key: str) -> bool:
        return bool(self.config.get(site_key, {}).get("use_flaresolverr", False))

    def site_uses_stealth(self, site_key: str) -> bool:
        return bool(self.config.get(site_key, {}).get("use_stealth", False))

    def site_proxy(self, site_key: str) -> str | None:
        """Резолвит `${VAR}` и `${VAR:-default}` из переменных окружения.

        Это нужно, чтобы в YAML коммитить только ссылку на env-переменную,
        а сам адрес прокси жил в .env на сервере (требование CLAUDE.md).
        """
        import os
        import re
        raw = self.config.get(site_key, {}).get("proxy")
        if not raw:
            return None
        raw = str(raw)

        def _expand(match: "re.Match[str]") -> str:
            inner = match.group(1)
            if ":-" in inner:
                var, default = inner.split(":-", 1)
                return os.getenv(var, default)
            return os.getenv(inner, "")

        resolved = re.sub(r"\$\{([^}]+)\}", _expand, raw).strip()
        return resolved or None

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
        # Unix-timestamp (tass.com <dateformat time="1776222001" mode="abs">)
        s = (raw or "").strip()
        if s.isdigit() and 9 <= len(s) <= 13:
            from datetime import datetime, timezone
            ts = int(s)
            if len(s) == 13:  # миллисекунды
                ts //= 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        try:
            return date_parser.parse(s).isoformat()
        except (ValueError, TypeError):
            return s or None
