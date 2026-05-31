"""MarquisCraftBot polling worker — stdlib only.

Отдельный процесс, чтобы не конфликтовать с локальным @TeamCaptainBot
(разные токены → нет 409). Читает токен из
  ~/.claude/channels/marquiscraft/.env  (TELEGRAM_BOT_TOKEN=...)

Что делает:
  * long-polling getUpdates (timeout 30s, интервал сна между итерациями 2s)
  * каждое текстовое сообщение:
      - пишет в bot/data/marquis_inbox.jsonl (одна строка JSON)
      - логирует в bot/logs/marquis.log
      - автоматически отвечает ack-сообщением
  * /start команда — приветственный ответ
  * корректно переживает сетевые ошибки (retry с backoff)

Запуск:
    py bot/marquis_bot.py
  или
    bot\\start_marquis.bat    (Windows)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BOT_DIR = Path(__file__).parent.resolve()
LOG_DIR = BOT_DIR / "logs"
DATA_DIR = BOT_DIR / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

INBOX = DATA_DIR / "marquis_inbox.jsonl"
LOG_FILE = LOG_DIR / "marquis.log"

TG_API = "https://api.telegram.org"
LONG_POLL_TIMEOUT = 30
POLL_INTERVAL = float(os.getenv("MARQUIS_POLL_INTERVAL", "2.0"))
ACK_TEXT = os.getenv(
    "MARQUIS_ACK_TEXT",
    "Принято. Сообщение сохранено и передано в Claude Code для обработки.",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s marquis: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("marquis")


def _env_file() -> Path:
    return Path(os.path.expanduser("~")) / ".claude" / "channels" / "marquiscraft" / ".env"


def _load_token() -> str:
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        return env_token.strip()
    path = _env_file()
    if not path.is_file():
        raise SystemExit(
            f"marquis_bot: token not found. Set TELEGRAM_BOT_TOKEN env var or put "
            f"TELEGRAM_BOT_TOKEN=... into {path}."
        )
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == "TELEGRAM_BOT_TOKEN":
            return v.strip().strip('"').strip("'")
    raise SystemExit(f"marquis_bot: TELEGRAM_BOT_TOKEN not found in {path}")


def _call(token: str, method: str, params: dict | None = None, timeout: int = 35) -> dict:
    url = f"{TG_API}/bot{token}/{method}"
    data = None
    if params:
        data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8")
    parsed = json.loads(body)
    if not parsed.get("ok"):
        raise RuntimeError(f"{method} failed: {parsed.get('description')}")
    return parsed["result"]


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_inbox(record: dict) -> None:
    with INBOX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _handle_message(token: str, msg: dict) -> None:
    chat = msg.get("chat", {})
    frm = msg.get("from", {})
    text = msg.get("text", "")
    chat_id = chat.get("id")
    record = {
        "ts": _iso_now(),
        "chat_id": chat_id,
        "user_id": frm.get("id"),
        "username": frm.get("username"),
        "first_name": frm.get("first_name"),
        "text": text,
    }
    _append_inbox(record)
    log.info(
        "incoming chat_id=%s user=%s text=%r",
        chat_id, frm.get("username") or frm.get("id"), text[:200],
    )

    if text.startswith("/start"):
        reply = (
            "Привет. Это @MarquisCraftBot — облачный бот, привязан к Claude Code.\n"
            "Присылай сообщение — оно сохранится в inbox и я отвечу ack-ом."
        )
    else:
        reply = ACK_TEXT

    try:
        _call(token, "sendMessage", {"chat_id": chat_id, "text": reply})
    except Exception:
        log.exception("sendMessage failed for chat_id=%s", chat_id)


def main() -> None:
    token = _load_token()
    log.info("marquis_bot starting, inbox=%s", INBOX)

    # Release any hanging getUpdates connection from a previous process run.
    # Without this, Telegram returns 409 Conflict until the stale long-poll times out.
    try:
        _call(token, "close")
        time.sleep(2.0)
    except Exception:
        log.info("close ignored (likely no hanging session)")

    try:
        _call(token, "deleteWebhook", {"drop_pending_updates": "false"})
    except Exception:
        log.exception("deleteWebhook ignored")

    offset = 0
    backoff = 1.0
    while True:
        try:
            updates = _call(
                token,
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": LONG_POLL_TIMEOUT,
                    "allowed_updates": json.dumps(["message"]),
                },
                timeout=LONG_POLL_TIMEOUT + 10,
            )
            backoff = 1.0
            for upd in updates:
                offset = max(offset, upd["update_id"] + 1)
                msg = upd.get("message")
                if msg:
                    try:
                        _handle_message(token, msg)
                    except Exception:
                        log.exception("handler crashed on update_id=%s", upd.get("update_id"))
            time.sleep(POLL_INTERVAL)
        except urllib.error.HTTPError as e:
            log.error("HTTP %s on getUpdates, sleep %.1fs", e.code, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            log.error("transport error: %s, sleep %.1fs", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
        except KeyboardInterrupt:
            log.info("stopped by user")
            return
        except Exception:
            log.exception("unexpected error, sleep %.1fs", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


if __name__ == "__main__":
    main()
