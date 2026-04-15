"""Асинхронная работа с SQLite: products + price_history."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    url             TEXT NOT NULL,
    name            TEXT NOT NULL,
    current_price   REAL,
    last_price      REAL,
    check_interval  INTEGER NOT NULL DEFAULT 30,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_checked    TIMESTAMP,
    UNIQUE(user_id, url)
);

CREATE TABLE IF NOT EXISTS price_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER NOT NULL,
    price        REAL NOT NULL,
    recorded_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_products_user ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_history_product ON price_history(product_id);
"""


@dataclass
class Product:
    id: int
    user_id: int
    url: str
    name: str
    current_price: Optional[float]
    last_price: Optional[float]
    check_interval: int
    created_at: str
    last_checked: Optional[str]


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.execute("PRAGMA foreign_keys = ON")
            await db.commit()

    async def add_product(
        self, user_id: int, url: str, name: str, price: Optional[float], interval: int = 30
    ) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """INSERT INTO products (user_id, url, name, current_price, check_interval)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, url) DO UPDATE SET name = excluded.name""",
                (user_id, url, name, price, interval),
            )
            product_id = cursor.lastrowid
            if price is not None:
                await db.execute(
                    "INSERT INTO price_history (product_id, price) VALUES (?, ?)",
                    (product_id, price),
                )
            await db.commit()
            return product_id

    async def list_products(self, user_id: int) -> list[Product]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM products WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [Product(**dict(r)) for r in rows]

    async def all_products(self) -> list[Product]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM products")
            rows = await cursor.fetchall()
            return [Product(**dict(r)) for r in rows]

    async def remove_product(self, user_id: int, product_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "DELETE FROM products WHERE id = ? AND user_id = ?",
                (product_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_price(self, product_id: int, new_price: float) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """UPDATE products
                   SET last_price = current_price,
                       current_price = ?,
                       last_checked = ?
                   WHERE id = ?""",
                (new_price, datetime.utcnow().isoformat(), product_id),
            )
            await db.execute(
                "INSERT INTO price_history (product_id, price) VALUES (?, ?)",
                (product_id, new_price),
            )
            await db.commit()

    async def touch_checked(self, product_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE products SET last_checked = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), product_id),
            )
            await db.commit()
