"""Claude CLI wrapper — simple one-shot mode (no session persistence)."""
import asyncio
import logging
import os
import time
from pathlib import Path

from config import (
    SYSTEM_PROMPT_PATH, CLAUDE_MODEL, CLAUDE_CLI, CLAUDE_TIMEOUT,
    PROJECT_DIR, CLAUDE_EXTRA_ARGS,
)

log = logging.getLogger(__name__)

_system_cache: dict[str, str] = {}


def load_system_prompt(reload: bool = False) -> str:
    key = str(SYSTEM_PROMPT_PATH)
    if not reload and key in _system_cache:
        return _system_cache[key]
    path = Path(SYSTEM_PROMPT_PATH)
    text = path.read_text(encoding="utf-8") if path.exists() else "Ты полезный ассистент."
    _system_cache[key] = text
    return text


async def ask(user_text: str, chat_id: int, system_prompt: str | None = None) -> str:
    system_text = system_prompt or load_system_prompt()

    cmd = [
        CLAUDE_CLI,
        "--print",
        "--output-format", "text",
        "--model", CLAUDE_MODEL,
        "--dangerously-skip-permissions",
        "--append-system-prompt", system_text,
        *CLAUDE_EXTRA_ARGS,
    ]

    log.info(
        "claude call chat=%s len=%d timeout=%ss model=%s",
        chat_id, len(user_text), CLAUDE_TIMEOUT, CLAUDE_MODEL,
    )
    started = time.monotonic()

    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    # Claude CLI блокирует --dangerously-skip-permissions без IS_SANDBOX=1 в нестандартных
    # окружениях; бот физически не может ответить на интерактивные prompt-ы, поэтому
    # помечаем окружение как sandbox.
    env["IS_SANDBOX"] = "1"

    # На Windows Claude CLI обычно — это .cmd shim. asyncio.create_subprocess_exec не
    # умеет искать .cmd через PATHEXT напрямую, поэтому на Windows используем shell=True
    # эквивалент через create_subprocess_shell с корректным квотированием.
    if os.name == "nt":
        # На Windows .cmd shim (claude.cmd) не запускается через create_subprocess_exec
        # напрямую. Используем shell-вариант с ручным quoting'ом под CreateProcess.
        cmdline = subprocess_join_windows(cmd)
        proc = await asyncio.create_subprocess_shell(
            cmdline,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_DIR),
            env=env,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_DIR),
            env=env,
        )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=user_text.encode("utf-8")),
            timeout=CLAUDE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        elapsed = time.monotonic() - started
        log.warning(
            "claude timeout chat=%s elapsed=%.1fs limit=%ss",
            chat_id, elapsed, CLAUDE_TIMEOUT,
        )
        raise RuntimeError(f"claude CLI timed out after {CLAUDE_TIMEOUT}s")

    elapsed = time.monotonic() - started

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        log.warning(
            "claude failed chat=%s elapsed=%.1fs rc=%s err=%s",
            chat_id, elapsed, proc.returncode, err[:300],
        )
        raise RuntimeError(f"claude CLI exited {proc.returncode}: {err[:500]}")

    out = stdout.decode("utf-8", errors="replace").strip()
    log.info(
        "claude done chat=%s elapsed=%.1fs out_len=%d",
        chat_id, elapsed, len(out),
    )
    return out


def subprocess_join_windows(args: list[str]) -> str:
    """Собрать command line для Windows CreateProcess.

    Правила quoting Windows: если аргумент содержит пробелы или кавычки — оборачиваем
    в двойные кавычки, внутренние кавычки удваиваем бэкслэшем (MS convention).
    """
    parts = []
    for a in args:
        if not a:
            parts.append('""')
            continue
        needs_quotes = any(c in a for c in ' \t"')
        if not needs_quotes:
            parts.append(a)
            continue
        # экранируем внутренние бэкслэши перед кавычкой и сами кавычки
        escaped = a.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'"{escaped}"')
    return " ".join(parts)
