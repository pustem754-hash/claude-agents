#!/usr/bin/env python3
"""
Lead Bot — Системное агентство ИИ
Получает заявки с сайта (HTTP /api/lead) и диалоги в Telegram,
пересылает владельцу (OWNER_ID).
"""
import asyncio
import html
import json
import logging
import os
from aiohttp import web
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("LEAD_BOT_TOKEN")
OWNER_ID = int(os.getenv("LEAD_BOT_OWNER_ID", "0"))
API_PORT = int(os.getenv("LEAD_API_PORT", "8001"))

if not BOT_TOKEN:
    raise RuntimeError("LEAD_BOT_TOKEN not set in environment")
if not OWNER_ID:
    raise RuntimeError("LEAD_BOT_OWNER_ID not set in environment")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("lead_bot.log"),
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("lead_bot")


WELCOME_TEXT = (
    "Здравствуйте! Я помогаю оставить заявку в Системное агентство ИИ.\n\n"
    "Напишите:\n"
    "1. Ваше имя\n"
    "2. Компания/проект\n"
    "3. Задача которую нужно решить\n\n"
    "Менеджер свяжется в течение часа."
)


# ─── Telegram handlers ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    logger.info("Start command from user_id=%s chat_id=%s", user.id, chat_id)

    if chat_id == OWNER_ID:
        await update.message.reply_text(
            "Бот активен. Буду пересылать сюда заявки с сайта и диалоги из Telegram.\n"
            f"Ваш chat_id: `{chat_id}`\n"
            f"API порт: {API_PORT}",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(WELCOME_TEXT)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text(f"Бот работает. API порт: {API_PORT}")


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"chat_id: `{chat_id}`\nuser_id: `{user_id}`",
        parse_mode="Markdown",
    )


def _user_label(user) -> str:
    parts = []
    full_name = (user.full_name or "").strip()
    if full_name:
        parts.append(full_name)
    if user.username:
        parts.append(f"@{user.username}")
    parts.append(f"id={user.id}")
    return " · ".join(parts)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пересылаем всё от незнакомцев владельцу как заявку."""
    if update.effective_chat.id == OWNER_ID:
        return
    if not update.message:
        return

    user = update.effective_user
    text = update.message.text or update.message.caption or ""
    label = _user_label(user)
    logger.info("Incoming lead message from %s", label)

    safe_text = html.escape(text) if text else "<i>(без текста)</i>"
    header = (
        "📬 <b>Новая заявка из Telegram</b>\n"
        f"От: <b>{html.escape(label)}</b>"
    )
    body = f"{header}\n\n{safe_text}"

    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=body,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        try:
            await context.bot.forward_message(
                chat_id=OWNER_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
            )
        except Exception as fwd_err:
            logger.warning("forward_message failed: %s", fwd_err)

        await update.message.reply_text(
            "Спасибо! Заявка принята — менеджер свяжется в течение часа."
        )
    except Exception as e:
        logger.exception("Failed to deliver message to owner: %s", e)
        await update.message.reply_text(
            "Не удалось отправить заявку. Попробуйте позже или напишите на pustem754@gmail.com"
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Ошибка при обработке события: %s", context.error, exc_info=context.error)


# ─── HTTP API ─────────────────────────────────────────────────────────────────

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


async def handle_lead(request: web.Request) -> web.Response:
    if request.method == "OPTIONS":
        return web.Response(status=204, headers=cors_headers())

    try:
        body = await request.json()
    except Exception:
        return web.Response(
            status=400,
            content_type="application/json",
            headers=cors_headers(),
            text=json.dumps({"ok": False, "error": "Invalid JSON"}),
        )

    name = str(body.get("name", "")).strip()
    company = str(body.get("company", "")).strip()
    task = str(body.get("task", "")).strip()

    if not name and not task:
        return web.Response(
            status=400,
            content_type="application/json",
            headers=cors_headers(),
            text=json.dumps({"ok": False, "error": "name or task required"}),
        )

    lines = ["📬 Новая заявка с сайта"]
    if name:
        lines.append(f"👤 Имя: {name}")
    if company:
        lines.append(f"🏢 Компания: {company}")
    if task:
        lines.append(f"📝 Задача: {task}")
    text = "\n".join(lines)

    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=OWNER_ID, text=text)
        logger.info("Lead sent to owner: name=%s company=%s", name, company)
        return web.Response(
            status=200,
            content_type="application/json",
            headers=cors_headers(),
            text=json.dumps({"ok": True}),
        )
    except Exception as e:
        logger.error("Failed to deliver lead: %s", e)
        return web.Response(
            status=500,
            content_type="application/json",
            headers=cors_headers(),
            text=json.dumps({"ok": False, "error": "Failed to deliver lead"}),
        )


async def handle_health(request: web.Request) -> web.Response:
    return web.Response(
        content_type="application/json",
        headers=cors_headers(),
        text=json.dumps({"ok": True, "service": "lead-bot-api"}),
    )


def build_web_app() -> web.Application:
    app = web.Application()
    app.router.add_route("OPTIONS", "/api/lead", handle_lead)
    app.router.add_post("/api/lead", handle_lead)
    app.router.add_get("/health", handle_health)
    return app


# ─── Main ─────────────────────────────────────────────────────────────────────

async def run_all() -> None:
    tg_app = Application.builder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", cmd_start))
    tg_app.add_handler(CommandHandler("status", cmd_status))
    tg_app.add_handler(CommandHandler("id", cmd_id))
    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    tg_app.add_error_handler(error_handler)

    web_app = build_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    logger.info("API server started on port %s", API_PORT)

    async with tg_app:
        await tg_app.start()
        logger.info("Telegram bot started. Leads will arrive to chat_id=%s", OWNER_ID)
        await tg_app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        try:
            await asyncio.Event().wait()
        finally:
            await tg_app.updater.stop()
            await tg_app.stop()
            await runner.cleanup()


def main() -> None:
    logger.info("Запуск Lead Bot + API (порт %s)...", API_PORT)
    asyncio.run(run_all())


if __name__ == "__main__":
    main()
