"""Воркер: читает ParseTask из news_urls, парсит и пишет в news_articles / news_errors."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from src.models import ParseError, ParseTask
from src.parser import ArticleParser
from src.queue import (
    QUEUE_ARTICLES,
    QUEUE_ERRORS,
    QUEUE_URLS,
    QueueConsumer,
    QueuePublisher,
)
from src.scraper import Scraper

load_dotenv()

CONFIG = Path(__file__).resolve().parent.parent / "config" / "sites.yaml"

logger = logging.getLogger("consumer")


def build_handler(publisher: QueuePublisher, scraper: Scraper, parser: ArticleParser):
    def handle(body: bytes) -> None:
        task = ParseTask.from_json(body)
        logger.info("Task received: %s (%s)", task.url, task.site_key)

        try:
            html = scraper.fetch(task.url, use_cloudflare=parser.site_uses_cloudflare(task.site_key))
            article = parser.parse(html, url=task.url, site_key=task.site_key)

            if not article.is_valid():
                raise ValueError("Article failed validation (missing title or too-short text)")

            publisher.publish(QUEUE_ARTICLES, article.to_json())
            logger.info("OK: %s (%d chars)", article.title[:80], len(article.text))

        except Exception as exc:
            logger.exception("Parse failed for %s", task.url)
            err = ParseError(url=task.url, site_key=task.site_key, error=str(exc))
            publisher.publish(QUEUE_ERRORS, err.to_json())

    return handle


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    scraper = Scraper()
    parser = ArticleParser(CONFIG)
    publisher = QueuePublisher()

    consumer = QueueConsumer(QUEUE_URLS, build_handler(publisher, scraper, parser))
    try:
        consumer.run()
    finally:
        publisher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
