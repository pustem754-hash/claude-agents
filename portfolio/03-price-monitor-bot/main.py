"""Точка входа: инициализация aiogram-бота, БД, скрапера и планировщика."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from src.bot import setup_router
from src.database import Database
from src.scheduler import setup_scheduler
from src.scraper import PriceScraper

load_dotenv()

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "bot.sqlite"


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN is not set. Copy .env.example to .env and fill it.")

    interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))

    db = Database(DB_PATH)
    await db.init()

    scraper = PriceScraper()
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(setup_router(db, scraper))

    scheduler = setup_scheduler(bot, db, scraper, interval)
    scheduler.start()
    logging.info("Scheduler started: interval %d min", interval)

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
