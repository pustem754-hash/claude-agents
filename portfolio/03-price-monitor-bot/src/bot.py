"""aiogram 3.x бот: команды /start /add /list /remove /help и FSM."""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .database import Database
from .scraper import PriceScraper

logger = logging.getLogger(__name__)

router = Router()

HELP_TEXT = (
    "<b>Price Monitor Bot</b>\n\n"
    "Отслеживаю цены на товары и присылаю уведомление, когда цена меняется.\n\n"
    "Команды:\n"
    "/add — добавить товар по ссылке\n"
    "/list — список отслеживаемых товаров\n"
    "/remove — удалить товар\n"
    "/help — эта справка\n\n"
    "Поддерживаемые сайты:\n"
    "Wildberries, Ozon, Yandex.Market, DNS, М.Видео, Citilink + универсальный парсер для любых shops.ru"
)


class AddProduct(StatesGroup):
    waiting_for_url = State()


def setup_router(db: Database, scraper: PriceScraper) -> Router:
    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer(HELP_TEXT, parse_mode="HTML")

    @router.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(HELP_TEXT, parse_mode="HTML")

    @router.message(Command("add"))
    async def cmd_add(message: Message, state: FSMContext) -> None:
        await state.set_state(AddProduct.waiting_for_url)
        await message.answer(
            "Пришлите ссылку на товар. Например:\n"
            "<code>https://www.wildberries.ru/catalog/12345678/detail.aspx</code>",
            parse_mode="HTML",
        )

    @router.message(AddProduct.waiting_for_url, F.text.startswith("http"))
    async def add_process_url(message: Message, state: FSMContext) -> None:
        url = message.text.strip()
        await message.answer("Парсю страницу товара, это займёт пару секунд…")

        try:
            scraped = scraper.get_price_and_name(url)
        except Exception as exc:
            logger.exception("Scrape failed: %s", exc)
            await message.answer(f"Не удалось загрузить страницу: <code>{exc}</code>", parse_mode="HTML")
            await state.clear()
            return

        await db.add_product(
            user_id=message.from_user.id,
            url=url,
            name=scraped.name,
            price=scraped.price,
        )
        price_str = f"{scraped.price:,.2f} руб.".replace(",", " ") if scraped.price else "не определена"
        await message.answer(
            f"Товар добавлен:\n<b>{scraped.name}</b>\nТекущая цена: {price_str}",
            parse_mode="HTML",
        )
        await state.clear()

    @router.message(AddProduct.waiting_for_url)
    async def add_bad_url(message: Message) -> None:
        await message.answer("Это не похоже на ссылку. Пришлите URL, начинающийся с http(s)://")

    @router.message(Command("list"))
    async def cmd_list(message: Message) -> None:
        products = await db.list_products(message.from_user.id)
        if not products:
            await message.answer("У вас пока нет отслеживаемых товаров. /add")
            return
        lines = ["<b>Ваши товары:</b>\n"]
        for p in products:
            price = f"{p.current_price:,.2f} руб.".replace(",", " ") if p.current_price else "—"
            lines.append(f"• <a href='{p.url}'>{p.name}</a>\n  цена: {price}")
        await message.answer(
            "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True
        )

    @router.message(Command("remove"))
    async def cmd_remove(message: Message) -> None:
        products = await db.list_products(message.from_user.id)
        if not products:
            await message.answer("Нет товаров для удаления.")
            return
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"🗑 {p.name[:40]}", callback_data=f"rm:{p.id}")]
                for p in products
            ]
        )
        await message.answer("Выберите товар для удаления:", reply_markup=kb)

    @router.callback_query(F.data.startswith("rm:"))
    async def on_remove(cb: CallbackQuery) -> None:
        product_id = int(cb.data.split(":", 1)[1])
        ok = await db.remove_product(cb.from_user.id, product_id)
        if ok:
            await cb.message.edit_text("Товар удалён.")
        else:
            await cb.message.edit_text("Не удалось удалить (возможно, уже удалён).")
        await cb.answer()

    return router


async def notify_price_change(
    bot: Bot, user_id: int, name: str, url: str, old: float, new: float
) -> None:
    diff = new - old
    pct = (diff / old) * 100 if old else 0
    arrow = "⬇️ упала" if diff < 0 else "⬆️ выросла"
    text = (
        f"💰 Цена {arrow}!\n\n"
        f"<b>{name}</b>\n"
        f"Было: {old:,.2f} руб.\n"
        f"Стало: {new:,.2f} руб.\n"
        f"Изменение: {diff:+,.2f} руб. ({pct:+.1f}%)\n\n"
        f"<a href='{url}'>Открыть товар</a>"
    ).replace(",", " ")
    try:
        await bot.send_message(user_id, text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as exc:
        logger.warning("Failed to notify user %d: %s", user_id, exc)
