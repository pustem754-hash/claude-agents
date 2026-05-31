"""TeamCaptainBot polling worker — Python replacement for bun/grammy plugin.

Stdlib polling + Claude CLI forward. Stable на Windows, не зависит от bun/grammy.

Что делает:
  * long-polling getUpdates (timeout 30s)
  * access-gate через ~/.claude/channels/telegram/access.json (allowFrom)
  * каждое текстовое сообщение:
      - пишет в bot/data/teams_inbox.jsonl
      - pipe в claude CLI (claude --print --model sonnet ...)
      - режет stdout на чанки 4096 (Telegram лимит) и шлёт sendMessage
  * /start — приветствие
  * 409 Conflict → sleep 30s + retry
  * ошибки сети с exponential backoff

ВАЖНО: перед запуском убедись что bun-плагин (telegram MCP) НЕ поллит
тот же токен — иначе 409 Conflict. Если плагин активен — убей:
    taskkill //F //IM bun.exe

Запуск:
    py bot/teams_bot.py
  или
    bot\\start_teams.bat
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BOT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = BOT_DIR.parent
LOG_DIR = BOT_DIR / "logs"
DATA_DIR = BOT_DIR / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

INBOX = DATA_DIR / "teams_inbox.jsonl"
LOG_FILE = LOG_DIR / "teams.log"

TG_API = "https://api.telegram.org"
LONG_POLL_TIMEOUT = 30
POLL_INTERVAL = float(os.getenv("TEAMS_POLL_INTERVAL", "1.0"))
TG_CHUNK = 4096

CLAUDE_CLI = os.getenv("CLAUDE_CLI", "claude")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "sonnet")
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "60"))

CHANNEL_DIR = Path(os.path.expanduser("~")) / ".claude" / "channels" / "telegram"
ENV_FILE = CHANNEL_DIR / ".env"
ACCESS_FILE = CHANNEL_DIR / "access.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s teams: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("teams")


def _load_token() -> str:
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        return env_token.strip()
    if not ENV_FILE.is_file():
        raise SystemExit(f"teams_bot: token not found, missing {ENV_FILE}")
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == "TELEGRAM_BOT_TOKEN":
            return v.strip().strip('"').strip("'")
    raise SystemExit(f"teams_bot: TELEGRAM_BOT_TOKEN not in {ENV_FILE}")


def _load_allowlist() -> set[str]:
    if not ACCESS_FILE.is_file():
        log.warning("access.json not found, allowlist empty — all messages ignored")
        return set()
    try:
        data = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
        return {str(x) for x in data.get("allowFrom", [])}
    except Exception as e:
        log.exception("failed parsing access.json: %s", e)
        return set()


def _tg_call(token: str, method: str, params: dict | None = None, timeout: int = 60) -> dict:
    url = f"{TG_API}/bot{token}/{method}"
    data = None
    if params is not None:
        encoded = {
            k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
            for k, v in params.items()
        }
        data = urllib.parse.urlencode(encoded).encode("utf-8")

    last_exc: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8")
            parsed = json.loads(body)
            if not parsed.get("ok"):
                raise RuntimeError(f"{method} failed: {parsed.get('description')}")
            return parsed["result"]
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_exc = e
            if attempt == 2:
                raise
            delay = 2 ** (attempt + 1)
            log.warning("%s transport retry %d/3 in %ds: %s", method, attempt + 1, delay, e)
            time.sleep(delay)
    raise last_exc  # type: ignore[misc]


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_inbox(record: dict) -> None:
    with INBOX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _chunks(text: str, limit: int = TG_CHUNK) -> list[str]:
    """Split text on paragraph/line boundaries when possible."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    buf = ""
    for para in text.split("\n\n"):
        piece = para + "\n\n"
        if len(piece) > limit:
            for line in piece.splitlines(keepends=True):
                if len(line) > limit:
                    for i in range(0, len(line), limit):
                        if buf:
                            parts.append(buf)
                            buf = ""
                        parts.append(line[i:i + limit])
                    continue
                if len(buf) + len(line) > limit:
                    parts.append(buf)
                    buf = line
                else:
                    buf += line
            continue
        if len(buf) + len(piece) > limit:
            parts.append(buf)
            buf = piece
        else:
            buf += piece
    if buf.strip():
        parts.append(buf)
    return [p.rstrip() for p in parts if p.strip()]


def _send_chunked(token: str, chat_id: int | str, text: str, reply_to: int | None = None) -> None:
    pieces = _chunks(text)
    for i, piece in enumerate(pieces):
        params: dict = {"chat_id": chat_id, "text": piece}
        if reply_to is not None and i == 0:
            params["reply_parameters"] = {"message_id": reply_to}
        try:
            _tg_call(token, "sendMessage", params)
        except Exception:
            log.exception("sendMessage chunk=%d/%d failed chat=%s", i + 1, len(pieces), chat_id)


def _send_typing(token: str, chat_id: int | str) -> None:
    try:
        _tg_call(token, "sendChatAction", {"chat_id": chat_id, "action": "typing"}, timeout=10)
    except Exception:
        pass


SYSTEM_PROMPT = (
    "Ты ассистент в Telegram-боте @TeamCaptainBot. Проект: claude-agents (Python, Node).\n"
    "Отвечай на русском, кратко и по делу.\n"
    "Разрешены только read-only команды: Read, Grep, Glob, Bash(git log/ls/cat/wc/find).\n"
    "Для счёта файлов используй: Glob + len(), либо Bash(find -type f | wc -l)."
)


def _call_claude(user_text: str, chat_id: int) -> str:
    cmd = [
        CLAUDE_CLI,
        "--print",
        "--output-format", "text",
        "--model", CLAUDE_MODEL,
        "--allowed-tools", "Read,Grep,Glob",
    ]
    prompt = "Ты краткий помощник. Отвечай на русском. Вопрос: " + user_text

    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["IS_SANDBOX"] = "1"

    log.info("claude call chat=%s len=%d timeout=%ss", chat_id, len(user_text), CLAUDE_TIMEOUT)
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            input=prompt.encode("utf-8"),
            capture_output=True,
            cwd=str(BOT_DIR),
            env=env,
            timeout=CLAUDE_TIMEOUT,
            shell=(os.name == "nt"),
        )
    except subprocess.TimeoutExpired:
        log.warning("claude timeout chat=%s elapsed=%.1fs", chat_id, time.monotonic() - started)
        return f"⏱ Claude CLI timeout after {CLAUDE_TIMEOUT}s."
    except FileNotFoundError as e:
        log.exception("claude CLI not found: %s", e)
        return f"⚠️ claude CLI не найден (CLAUDE_CLI={CLAUDE_CLI})."

    elapsed = time.monotonic() - started
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()[:500]
        log.warning("claude rc=%s elapsed=%.1fs err=%s", proc.returncode, elapsed, err)
        return f"⚠️ Claude CLI exited {proc.returncode}\n{err}"

    out = proc.stdout.decode("utf-8", errors="replace").strip()
    log.info("claude done chat=%s elapsed=%.1fs out_len=%d", chat_id, elapsed, len(out))
    return out or "(пустой ответ)"


def _handle_message(token: str, allowlist: set[str], msg: dict) -> None:
    chat = msg.get("chat", {})
    frm = msg.get("from", {})
    text = msg.get("text", "") or msg.get("caption", "")
    chat_id = chat.get("id")
    user_id = frm.get("id")
    mid = msg.get("message_id")

    if allowlist and str(user_id) not in allowlist and str(chat_id) not in allowlist:
        log.info("blocked non-allowlist user_id=%s chat_id=%s", user_id, chat_id)
        return

    record = {
        "ts": _iso_now(),
        "chat_id": chat_id,
        "user_id": user_id,
        "username": frm.get("username"),
        "first_name": frm.get("first_name"),
        "message_id": mid,
        "text": text,
    }
    _append_inbox(record)
    log.info("incoming chat=%s user=%s text=%r", chat_id, frm.get("username") or user_id, text[:200])

    if not text:
        _send_chunked(token, chat_id, "Пришли текст — пока поддерживаю только текст.", reply_to=mid)
        return

    if text.startswith("/start"):
        _send_chunked(
            token, chat_id,
            "Привет. @TeamCaptainBot на Python polling.\n"
            "Пиши запрос — пересылаю в Claude Code и возвращаю ответ.",
            reply_to=mid,
        )
        return

    _send_typing(token, chat_id)
    reply = _call_claude(text, chat_id)
    _send_chunked(token, chat_id, reply, reply_to=mid)


def main() -> None:
    token = _load_token()
    allowlist = _load_allowlist()
    log.info("teams_bot starting, allowlist_size=%d inbox=%s", len(allowlist), INBOX)

    try:
        _tg_call(token, "close")
        time.sleep(2.0)
    except Exception:
        log.info("close ignored (no hanging session)")

    try:
        _tg_call(token, "deleteWebhook", {"drop_pending_updates": "false"})
    except Exception:
        log.exception("deleteWebhook ignored")

    offset = 0
    backoff = 1.0
    while True:
        try:
            updates = _tg_call(
                token,
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": LONG_POLL_TIMEOUT,
                    "allowed_updates": ["message"],
                },
                timeout=LONG_POLL_TIMEOUT + 10,
            )
            backoff = 1.0
            for upd in updates:
                offset = max(offset, upd["update_id"] + 1)
                msg = upd.get("message")
                if msg:
                    try:
                        _handle_message(token, allowlist, msg)
                    except Exception:
                        log.exception("handler crashed upd_id=%s", upd.get("update_id"))
            time.sleep(POLL_INTERVAL)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            log.error("HTTP %s on getUpdates body=%s sleep=%.1fs", e.code, body, backoff)
            if e.code == 409:
                time.sleep(30.0)
                backoff = 1.0
            else:
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            log.error("transport: %s sleep=%.1fs", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
        except KeyboardInterrupt:
            log.info("stopped by user")
            return
        except Exception:
            log.exception("unexpected, sleep=%.1fs", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


if __name__ == "__main__":
    main()
