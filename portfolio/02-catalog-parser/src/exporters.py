"""Экспорт товаров в CSV и JSON."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

FIELDS = (
    "id", "name", "brand", "price", "original_price",
    "image", "url", "availability", "rating", "reviews",
)


def export_csv(path: str | Path, products: Iterable[dict]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    # UTF-8 BOM для корректного открытия в Excel
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for p in products:
            writer.writerow({k: p.get(k, "") for k in FIELDS})
            count += 1
    return count


def export_json(path: str | Path, products: list[dict]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"total": len(products), "products": products}
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return len(products)
