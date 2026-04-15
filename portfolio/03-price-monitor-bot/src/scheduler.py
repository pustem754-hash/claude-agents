"""APScheduler-задача: периодически проверяет цены и шлёт уведомления."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .bot import notify_price_change
from .database import Database
from .scraper import PriceScraper

logger = logging.getLogger(__name__)


async def check_all_prices(bot: Bot, db: Database, scraper: PriceScraper) -> None:
    products = await db.all_products()
    logger.info("Checking %d products", len(products))

    for product in products:
        try:
            scraped = await asyncio.to_thread(scraper.get_price_and_name, product.url)
        except Exception as exc:
            logger.warning("Check failed for %s: %s", product.url, exc)
            await db.touch_checked(product.id)
            continue

        if scraped.price is None:
            await db.touch_checked(product.id)
            continue

        old = product.current_price
        if old is None or abs(scraped.price - old) < 0.01:
            await db.touch_checked(product.id)
            continue

        await db.update_price(product.id, scraped.price)
        await notify_price_change(
            bot, product.user_id, scraped.name or product.name, product.url, old, scraped.price
        )


def setup_scheduler(bot: Bot, db: Database, scraper: PriceScraper, interval_minutes: int) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        check_all_prices,
        "interval",
        minutes=interval_minutes,
        args=(bot, db, scraper),
        id="price_check",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
