"""CLI-точка входа: запуск парсинга по конфигу и экспорт в CSV/JSON."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.exporters import export_csv, export_json
from src.parser import CatalogParser

load_dotenv()

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"


def resolve_config(name: str) -> Path:
    path = Path(name)
    if path.is_file():
        return path
    candidate = CONFIG_DIR / f"{name}.yaml"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Config not found: {name}")


def run_one(config_path: Path, output_dir: Path, query: str | None) -> int:
    parser = CatalogParser(config_path)
    products = parser.run(query=query)

    output_conf = parser.config.get("output", {})
    csv_file = output_dir / output_conf.get("csv_file", f"{config_path.stem}.csv")
    json_file = output_dir / output_conf.get("json_file", f"{config_path.stem}.json")

    export_csv(csv_file, products)
    export_json(json_file, products)

    logging.info("Saved %d products -> %s, %s", len(products), csv_file.name, json_file.name)
    return len(products)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    ap = argparse.ArgumentParser(description="Catalog parser — WB / Ozon / generic HTML.")
    ap.add_argument("--config", help="Имя конфига (wildberries, ozon, ...) или путь к YAML")
    ap.add_argument("--query", help="Поисковый запрос (для API-режимов)")
    ap.add_argument("--output", default=str(OUTPUT_DIR), help="Директория результатов")
    ap.add_argument("--all", action="store_true", help="Запустить все конфиги из config/")
    args = ap.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        total = 0
        for cfg in sorted(CONFIG_DIR.glob("*.yaml")):
            total += run_one(cfg, output_dir, query=args.query)
        logging.info("All done: %d products in total", total)
        return 0

    if not args.config:
        ap.error("--config or --all is required")

    run_one(resolve_config(args.config), output_dir, query=args.query)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
