"""CLI для добавления URL в очередь news_urls и просмотра статуса очередей."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from src.models import ParseTask
from src.queue import QUEUE_URLS, QueuePublisher

load_dotenv()

DEMO_TASKS = [
    ParseTask(url="https://lenta.ru/news/2026/04/10/example/", site_key="lenta_ru"),
    ParseTask(url="https://www.rbc.ru/business/10/04/2026/abcdef/", site_key="rbc_ru"),
    ParseTask(url="https://tass.ru/ekonomika/12345678", site_key="tass_ru"),
]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    ap = argparse.ArgumentParser(description="Add URLs to RabbitMQ news_urls queue.")
    ap.add_argument("--url", help="URL статьи")
    ap.add_argument("--site", help="site_key из config/sites.yaml")
    ap.add_argument("--demo", action="store_true", help="Добавить набор демо-URL")
    ap.add_argument("--status", action="store_true", help="Показать статистику очередей")
    args = ap.parse_args()

    pub = QueuePublisher()
    try:
        if args.status:
            stats = pub.queue_stats()
            for q, n in stats.items():
                print(f"{q:<16} {n}")
            return 0

        if args.demo:
            for task in DEMO_TASKS:
                pub.publish(QUEUE_URLS, task.to_json())
                logging.info("Enqueued demo: %s", task.url)
            return 0

        if not args.url or not args.site:
            ap.error("--url and --site are required (or use --demo/--status)")

        task = ParseTask(url=args.url, site_key=args.site)
        pub.publish(QUEUE_URLS, task.to_json())
        logging.info("Enqueued: %s -> %s", args.site, args.url)
        return 0
    finally:
        pub.close()


if __name__ == "__main__":
    raise SystemExit(main())
