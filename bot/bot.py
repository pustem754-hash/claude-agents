"""Claude-powered Telegram bot — aiogram 3, text + photo + document + PDF reply.

Local (@TeamCaptainBot) mirror of the VPS @MarquisCraftBot. Identical pipeline:
Claude CLI prints its answer, the bot scans that answer for absolute paths to
.pdf files on disk and attaches each one as a Telegram document.

Difference vs VPS bot: PDF_PATH_RE supports Windows paths (C:\\... / C:/...)
in addition to unix-style absolute paths, so it works on the local machine.
"""
import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, Message

import history
from claude_client import ask, load_system_prompt
from config import (
    ADMIN_IDS,
    BOT_DIR,
    BOT_TOKEN,
    CLAUDE_MODEL,
    LOG_LEVEL,
    MAX_MESSAGE_LEN,
)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher()

PHOTOS_DIR = BOT_DIR / "data" / "photos"
DOCS_DIR = BOT_DIR / "data" / "docs"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Абсолютные пути до .pdf. Поддерживаем:
#   * Windows: C:\Users\...\file.pdf, C:/Users/.../file.pdf
#   * Unix:    /home/.../file.pdf
# Не захватываем пробелы и типовые ограничители.
PDF_PATH_RE = re.compile(
    r"""(
        [A-Za-z]:[\\/][^\s`()\[\]<>"']+\.pdf      # Windows absolute
        |
        /[^\s`()\[\]<>"'\\]+\.pdf                 # Unix absolute
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Интервал переотправки chat action. Telegram гасит индикатор через ~5 сек.
TYPING_REFRESH_SEC = 4.0


def is_admin(user_id: int) -> bool:
    return not ADMIN_IDS or user_id in ADMIN_IDS


def chunk(text: str, size: int = MAX_MESSAGE_LEN) -> list[str]:
    if len(text) <= size:
        return [text]
    out, buf = [], ""
    for para in text.split("\n\n"):
        if len(buf) + len(para) + 2 > size:
            if buf:
                out.append(buf)
            if len(para) > size:
                for i in range(0, len(para), size):
                    out.append(para[i:i + size])
                buf = ""
            else:
                buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        out.append(buf)
    return out


def extract_pdf_paths(text: str) -> list[str]:
    """Находит в тексте абсолютные пути до .pdf, дедуплицирует, сохраняет порядок."""
    seen: set[str] = set()
    result: list[str] = []
    for match in PDF_PATH_RE.findall(text or ""):
        # re.VERBOSE + single capture group => match is a string
        if match not in seen:
            seen.add(match)
            result.append(match)
    return result


async def _chat_action_loop(chat_id: int, action: ChatAction) -> None:
    """Фоновая задача: держит chat action живым, переотправляя его каждые TYPING_REFRESH_SEC."""
    try:
        while True:
            try:
                await bot.send_chat_action(chat_id, action)
            except Exception:
                log.debug("chat action refresh failed", exc_info=True)
            await asyncio.sleep(TYPING_REFRESH_SEC)
    except asyncio.CancelledError:
        pass


def start_chat_action(chat_id: int, action: ChatAction = ChatAction.TYPING) -> asyncio.Task:
    return asyncio.create_task(_chat_action_loop(chat_id, action))


async def stop_chat_action(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


async def send_answer(msg: Message, answer: str) -> None:
    """Отправляет текст чанками, затем прикрепляет найденные в ответе PDF-файлы."""
    for part in chunk(answer):
        await msg.answer(part)

    pdf_paths = extract_pdf_paths(answer)
    if not pdf_paths:
        return

    upload_task = start_chat_action(msg.chat.id, ChatAction.UPLOAD_DOCUMENT)
    try:
        for path_str in pdf_paths:
            path = Path(path_str)
            if not path.is_file():
                log.info("PDF path mentioned but not found on disk: %s", path_str)
                continue
            try:
                await msg.answer_document(FSInputFile(str(path)))
                log.info("Sent PDF attachment: %s", path_str)
            except Exception:
                log.exception("Failed to send PDF %s", path_str)
    finally:
        await stop_chat_action(upload_task)


@dp.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    await msg.answer(
        f"Привет. Я обёртка над claude CLI (модель {CLAUDE_MODEL}).\n"
        "Использую Max-подписку, API-ключ не нужен.\n\n"
        "Принимаю текст и фото, могу отправлять PDF-файлы.\n\n"
        "Команды:\n"
        "/clear — сбросить счётчик турнов\n"
        "/reload — перечитать CLAUDE.md (админ)\n"
        "/stats — статистика\n"
        "/model — текущая модель\n\n"
        "Пиши — я отвечаю."
    )


@dp.message(Command("clear"))
async def cmd_clear(msg: Message) -> None:
    history.clear(msg.chat.id)
    await msg.answer("Счётчик сброшен.")


@dp.message(Command("reload"))
async def cmd_reload(msg: Message) -> None:
    if not is_admin(msg.from_user.id):
        await msg.answer("Только для админа.")
        return
    load_system_prompt(reload=True)
    await msg.answer("CLAUDE.md перечитан.")


@dp.message(Command("stats"))
async def cmd_stats(msg: Message) -> None:
    t = history.turns(msg.chat.id)
    await msg.answer(
        f"Турнов: {t}\n"
        f"Сейчас: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


@dp.message(Command("model"))
async def cmd_model(msg: Message) -> None:
    await msg.answer(f"Модель: {CLAUDE_MODEL}")


async def _process_prompt(msg: Message, prompt: str) -> None:
    """Общий pipeline: typing keepalive → ask → error handling → history → send_answer."""
    chat_id = msg.chat.id

    typing_task = start_chat_action(chat_id, ChatAction.TYPING)
    try:
        try:
            answer = await ask(prompt, chat_id)
        except Exception as e:
            log.exception("claude CLI call failed")
            err_text = str(e)[:500]
            await msg.answer(f"Ошибка claude CLI: {err_text}")
            return

        if not answer:
            await msg.answer("Claude вернул пустой ответ. Попробуй переформулировать.")
            return

        history.record_turn(chat_id)
    finally:
        await stop_chat_action(typing_task)

    await send_answer(msg, answer)


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(msg: Message) -> None:
    if not is_admin(msg.from_user.id):
        await msg.answer("Доступ ограничен.")
        return
    await _process_prompt(msg, msg.text or "")


@dp.message(F.photo)
async def handle_photo(msg: Message) -> None:
    if not is_admin(msg.from_user.id):
        await msg.answer("Доступ ограничен.")
        return

    photo = msg.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        local = PHOTOS_DIR / f"{msg.chat.id}_{msg.message_id}.jpg"
        await bot.download_file(file.file_path, destination=str(local))
    except Exception as e:
        log.exception("failed to download photo")
        await msg.answer(f"Не удалось скачать фото: {str(e)[:300]}")
        return

    caption = (msg.caption or "").strip()
    if not caption:
        caption = "Опиши, что на изображении."
    prompt = f"Пользователь прислал изображение: {local}\n\nЗапрос: {caption}"
    log.info("photo saved: %s", local)
    await _process_prompt(msg, prompt)


@dp.message(F.document)
async def handle_document(msg: Message) -> None:
    if not is_admin(msg.from_user.id):
        await msg.answer("Доступ ограничен.")
        return

    doc = msg.document
    try:
        file = await bot.get_file(doc.file_id)
        safe_name = doc.file_name or "file"
        local = DOCS_DIR / f"{msg.chat.id}_{msg.message_id}_{safe_name}"
        await bot.download_file(file.file_path, destination=str(local))
    except Exception as e:
        log.exception("failed to download document")
        await msg.answer(f"Не удалось скачать файл: {str(e)[:300]}")
        return

    caption = (msg.caption or "").strip()
    if not caption:
        caption = "Опиши, что в этом файле."
    prompt = f"Пользователь прислал документ: {local}\n\nЗапрос: {caption}"
    log.info("document saved: %s", local)
    await _process_prompt(msg, prompt)


@dp.message()
async def fallback(msg: Message) -> None:
    await msg.answer("Принимаю текст, фото и документы.")


async def main() -> None:
    log.info("Bot starting. Model=%s", CLAUDE_MODEL)
    load_system_prompt()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped")
