"""Тест парсера без очереди: прогоняет один URL и печатает результат."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parser import ArticleParser
from src.scraper import Scraper

CONFIG = Path(__file__).resolve().parent.parent / "config" / "sites.yaml"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--site", required=True)
    args = ap.parse_args()

    parser = ArticleParser(CONFIG)
    scraper = Scraper()

    html = scraper.fetch(
        args.url,
        use_cloudflare=parser.site_uses_cloudflare(args.site),
        use_playwright=parser.site_uses_playwright(args.site),
        use_flaresolverr=parser.site_uses_flaresolverr(args.site),
        use_stealth=parser.site_uses_stealth(args.site),
        site_key=args.site,
        proxy=parser.site_proxy(args.site),
    )
    article = parser.parse(html, url=args.url, site_key=args.site)

    print(f"Title:  {article.title}")
    print(f"Author: {article.author}")
    print(f"Date:   {article.published_at}")
    print(f"Length: {len(article.text)} chars")
    print(f"Valid:  {article.is_valid()}")
    print("---\n" + article.text[:500] + ("..." if len(article.text) > 500 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
