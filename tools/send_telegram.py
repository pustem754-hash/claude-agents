"""Отправка файлов и сообщений в Telegram напрямую через Bot API.

НЕ поллит, НЕ подменяет плагин. Это fallback-инструмент, который любой агент
или shell могут вызвать. Работает даже если Claude Code плагин отключён или
упал.

Токен берётся из (в порядке приоритета):
  1) env TELEGRAM_BOT_TOKEN
  2) файла %USERPROFILE%\\.claude\\channels\\telegram\\.env (тот же, что у плагина)
  3) bot/.env проекта

Usage:
    # сообщение
    py tools/send_telegram.py <chat_id> --text "привет"

    # файл (документ или фото по расширению)
    py tools/send_telegram.py <chat_id> --file "C:/path/report.pdf"
    py tools/send_telegram.py <chat_id> --file "C:/path/chart.png" --caption "Q4"

    # сообщение + несколько файлов
    py tools/send_telegram.py <chat_id> --text "готово" --file a.pdf --file b.xlsx

Exit codes: 0 ok, 1 bad args, 2 transport error, 3 Telegram API error.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEFAULT_TIMEOUT = 60
TG_API = "https://api.telegram.org"
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _resolve_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        return token.strip()

    candidates = [
        Path(os.path.expanduser("~")) / ".claude" / "channels" / "telegram" / ".env",
        Path(__file__).resolve().parents[1] / "bot" / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]
    for c in candidates:
        if not c.is_file():
            continue
        try:
            for line in c.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() in ("TELEGRAM_BOT_TOKEN", "BOT_TOKEN"):
                    return v.strip().strip('"').strip("'")
        except OSError:
            continue

    sys.stderr.write(
        "send_telegram: token not found. Set TELEGRAM_BOT_TOKEN env var or put it "
        "into ~/.claude/channels/telegram/.env or bot/.env.\n"
    )
    raise SystemExit(1)


def _post_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    return _call(req, timeout)


def _post_multipart(url: str, fields: dict, files: dict, timeout: int) -> dict:
    """Minimal multipart/form-data client. files = {field: (filename, bytes, content_type)}."""
    boundary = uuid.uuid4().hex
    body = bytearray()
    for k, v in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        body.extend(str(v).encode("utf-8"))
        body.extend(b"\r\n")
    for field, (filename, content, ctype) in files.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode()
        )
        body.extend(f"Content-Type: {ctype}\r\n\r\n".encode())
        body.extend(content)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        url, data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    return _call(req, timeout)


def _call(req: urllib.request.Request, timeout: int) -> dict:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8")
                parsed = json.loads(raw)
                if not parsed.get("ok"):
                    raise TelegramApiError(parsed.get("description") or raw[:300], parsed)
                return parsed
        except urllib.error.HTTPError as e:
            # Try to parse Telegram error JSON
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                raise TelegramApiError(err_body.get("description") or str(e), err_body) from e
            except (json.JSONDecodeError, ValueError):
                raise TelegramApiError(f"HTTP {e.code}: {e.reason}", {"http": e.code}) from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_exc = e
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise TransportError(str(e)) from e
    assert last_exc is not None
    raise TransportError(str(last_exc))


class TransportError(RuntimeError):
    pass


class TelegramApiError(RuntimeError):
    def __init__(self, msg: str, body: dict) -> None:
        super().__init__(msg)
        self.body = body


def send_message(chat_id: str, text: str, *, reply_to: int | None = None,
                 parse_mode: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> int:
    token = _resolve_token()
    payload: dict = {"chat_id": chat_id, "text": text}
    if reply_to is not None:
        payload["reply_parameters"] = {"message_id": reply_to}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    res = _post_json(f"{TG_API}/bot{token}/sendMessage", payload, timeout)
    return int(res["result"]["message_id"])


def send_file(chat_id: str, file_path: str | os.PathLike[str], *,
              caption: str | None = None, reply_to: int | None = None,
              timeout: int = DEFAULT_TIMEOUT) -> int:
    token = _resolve_token()
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError(f"file > 50 MB (Telegram bot limit): {path}")

    ext = path.suffix.lower()
    is_photo = ext in PHOTO_EXTS
    endpoint = "sendPhoto" if is_photo else "sendDocument"
    field = "photo" if is_photo else "document"
    ctype = mimetypes.guess_type(path.name)[0] or ("image/jpeg" if is_photo else "application/octet-stream")

    fields: dict = {"chat_id": chat_id}
    if caption:
        fields["caption"] = caption
    if reply_to is not None:
        fields["reply_parameters"] = json.dumps({"message_id": reply_to})

    with path.open("rb") as f:
        data = f.read()

    res = _post_multipart(
        f"{TG_API}/bot{token}/{endpoint}",
        fields=fields,
        files={field: (path.name, data, ctype)},
        timeout=timeout,
    )
    return int(res["result"]["message_id"])


def _cli() -> int:
    p = argparse.ArgumentParser(description="Send Telegram message/file via Bot API.")
    p.add_argument("chat_id", help="Telegram chat id (int-as-string)")
    p.add_argument("--text", help="Text to send (before files if both given)")
    p.add_argument("--file", action="append", default=[], help="File path(s) to attach")
    p.add_argument("--caption", help="Caption for files (applies to first file)")
    p.add_argument("--reply-to", type=int, help="message_id to thread under")
    p.add_argument("--parse-mode", choices=["MarkdownV2", "HTML"], default=None)
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if not args.text and not args.file:
        p.error("need --text or --file")

    sent: list[int] = []
    try:
        if args.text:
            mid = send_message(
                args.chat_id, args.text,
                reply_to=args.reply_to, parse_mode=args.parse_mode, timeout=args.timeout,
            )
            sent.append(mid)
            if not args.quiet:
                print(f"text sent: id={mid}")

        for i, fp in enumerate(args.file):
            cap = args.caption if i == 0 else None
            mid = send_file(
                args.chat_id, fp,
                caption=cap, reply_to=args.reply_to, timeout=args.timeout,
            )
            sent.append(mid)
            if not args.quiet:
                print(f"file sent: {fp} id={mid}")
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except TelegramApiError as e:
        print(f"Telegram API error: {e}", file=sys.stderr)
        return 3
    except TransportError as e:
        print(f"transport error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
