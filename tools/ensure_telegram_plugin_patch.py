"""Идемпотентно применяет патч к Telegram-плагину Claude Code.

Проблема: grammy 1.41 + bun на Windows не умеет multipart через InputFile(Buffer),
падает с HttpError "Network request for sendDocument failed". Text-запросы работают
(JSON), а файлы — нет.

Фикс: в server.ts плагина вместо bot.api.sendDocument/sendPhoto использовать
прямой fetch + FormData + Blob. Это обходит кривой multipart-сериализатор grammy
в bun на Windows.

Запуск:
    py tools/ensure_telegram_plugin_patch.py            # применить патч ко всем
                                                         # установленным версиям
    py tools/ensure_telegram_plugin_patch.py --check    # только проверить, не менять

Скрипт идемпотентный: повторный запуск не делает ничего, если патч уже применён.
Запускай после обновления плагина или каждый раз, когда видишь ошибку
"Network request for sendDocument failed".
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

PATCH_MARKER = "bypass grammy for uploads"
OLD_BLOCK_START = "// Files go as separate messages"
OLD_BLOCK_BOT_API = "bot.api.sendDocument(chat_id, input, opts)"

NEW_BLOCK = """        // Files go as separate messages (Telegram doesn't mix text+file in one
        // sendMessage call). Thread under reply_to if present.
        //
        // grammy 1.41 + bun on Windows throws HttpError "Network request for
        // sendDocument failed" when InputFile wraps a Buffer — the internal
        // multipart serializer is incompatible with bun's fetch. Raw fetch
        // with a Blob-based FormData works, so we bypass grammy for uploads.
        for (const f of files) {
          const ext = extname(f).toLowerCase()
          const buf = readFileSync(f)
          const endpoint = PHOTO_EXTS.has(ext) ? 'sendPhoto' : 'sendDocument'
          const field = PHOTO_EXTS.has(ext) ? 'photo' : 'document'
          const fd = new FormData()
          fd.append('chat_id', chat_id)
          if (reply_to != null && replyMode !== 'off') {
            fd.append('reply_parameters', JSON.stringify({ message_id: reply_to }))
          }
          const blob = new Blob([buf])
          fd.append(field, blob, basename(f))
          const res = await fetch(`https://api.telegram.org/bot${TOKEN}/${endpoint}`, {
            method: 'POST',
            body: fd,
          })
          const body = (await res.json()) as { ok: boolean; result?: { message_id: number }; description?: string }
          if (!body.ok || !body.result) {
            throw new Error(`${endpoint} failed: ${body.description ?? `HTTP ${res.status}`}`)
          }
          sentIds.push(body.result.message_id)
        }"""


def find_plugin_versions() -> list[Path]:
    """Находит все закэшированные версии Telegram-плагина Claude Code."""
    home = Path(os.path.expanduser("~"))
    base = home / ".claude" / "plugins" / "cache" / "claude-plugins-official" / "telegram"
    if not base.is_dir():
        return []
    return [p for p in base.iterdir() if p.is_dir() and (p / "server.ts").is_file()]


def is_patched(server_ts: Path) -> bool:
    text = server_ts.read_text(encoding="utf-8")
    return PATCH_MARKER in text


def find_original_block(text: str) -> tuple[int, int] | None:
    """Возвращает (start, end) индексы исходного блока загрузки файлов."""
    start = text.find(OLD_BLOCK_START)
    if start == -1:
        return None
    # ищем закрывающую } блока for (const f of files) { ... }
    # опираемся на маркер — строку с sendDocument
    marker = text.find(OLD_BLOCK_BOT_API, start)
    if marker == -1:
        return None
    # от marker идём вперёд до строки, в которой есть только '}\n' (закрытие for)
    idx = text.find("\n        }\n", marker)
    if idx == -1:
        return None
    return (start, idx + len("\n        }"))


def apply_patch(server_ts: Path, *, dry_run: bool = False) -> str:
    """Возвращает одну из строк: 'already', 'patched', 'skipped:<reason>'."""
    text = server_ts.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        return "already"
    loc = find_original_block(text)
    if loc is None:
        return "skipped:block_not_found"

    start, end = loc
    new_text = text[:start] + NEW_BLOCK + text[end:]

    if dry_run:
        return "patched"

    backup = server_ts.with_suffix(
        server_ts.suffix + f".backup.{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    shutil.copy2(server_ts, backup)
    server_ts.write_text(new_text, encoding="utf-8")
    return "patched"


def main() -> int:
    p = argparse.ArgumentParser(description="Ensure Telegram plugin file-upload patch is applied.")
    p.add_argument("--check", action="store_true", help="only report status, don't modify")
    args = p.parse_args()

    versions = find_plugin_versions()
    if not versions:
        print("no Telegram plugin cache found at ~/.claude/plugins/cache/claude-plugins-official/telegram")
        return 0

    any_patched = False
    rc = 0
    for v in versions:
        server_ts = v / "server.ts"
        try:
            result = apply_patch(server_ts, dry_run=args.check)
        except Exception as e:
            print(f"  {v.name}: ERROR {e}")
            rc = 1
            continue
        if result == "already":
            print(f"  {v.name}: already patched [OK]")
        elif result == "patched":
            any_patched = True
            tag = "WOULD patch" if args.check else "patched"
            print(f"  {v.name}: {tag} -> restart plugin (/reload-plugins in Claude Code)")
        else:
            print(f"  {v.name}: {result}  (unfamiliar server.ts layout - no change)")
            rc = 1

    if args.check:
        return 0 if not any_patched else 2  # 2 = patch needed

    if any_patched:
        print("\nПатч применён. Теперь перезапусти плагин: /reload-plugins в Claude Code.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
