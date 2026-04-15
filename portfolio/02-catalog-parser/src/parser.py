"""Оркестратор: выбирает адаптер по режиму из YAML-конфига."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .adapters.html_parser import HtmlCatalogParser
from .adapters.ozon import OzonParser
from .adapters.wildberries import WildberriesParser
from .fetcher import HttpFetcher

logger = logging.getLogger(__name__)


class CatalogParser:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        with self.config_path.open("r", encoding="utf-8") as f:
            self.config: dict[str, Any] = yaml.safe_load(f) or {}
        self.fetcher = HttpFetcher(
            delay_min=self.config.get("rate_limit", {}).get("delay_min", 1.0),
            delay_max=self.config.get("rate_limit", {}).get("delay_max", 3.0),
        )

    def run(self, query: str | None = None) -> list[dict]:
        mode = self.config.get("mode")
        logger.info("Parsing %s in %s mode", self.config.get("name"), mode)

        if mode == "api":
            adapter = WildberriesParser(self.config, self.fetcher)
            return adapter.parse(query=query)
        if mode == "playwright":
            adapter = OzonParser(self.config)
            return adapter.parse()
        if mode == "html":
            adapter = HtmlCatalogParser(self.config, self.fetcher)
            return adapter.parse()

        raise ValueError(f"Unknown mode in config: {mode!r}")
