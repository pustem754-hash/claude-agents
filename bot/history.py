"""Track whether a claude CLI session already exists for a chat.

Actual conversation history is stored by the claude CLI itself (via --session-id).
We only track per-chat metadata: whether the session has been initialised and
a counter of turns for /stats.
"""
import json
from pathlib import Path
from typing import Any

from config import HISTORY_DIR

_STATE = HISTORY_DIR / "sessions.json"


def _load() -> dict[str, dict[str, Any]]:
    if not _STATE.exists():
        return {}
    try:
        return json.loads(_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, dict[str, Any]]) -> None:
    _STATE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get(chat_id: int) -> dict[str, Any]:
    return _load().get(str(chat_id), {"turns": 0, "initialised": False})


def is_first_turn(chat_id: int) -> bool:
    return not get(chat_id).get("initialised", False)


def record_turn(chat_id: int) -> None:
    data = _load()
    key = str(chat_id)
    entry = data.get(key, {"turns": 0, "initialised": False})
    entry["turns"] = entry.get("turns", 0) + 1
    entry["initialised"] = True
    data[key] = entry
    _save(data)


def clear(chat_id: int) -> None:
    data = _load()
    key = str(chat_id)
    if key in data:
        del data[key]
        _save(data)


def turns(chat_id: int) -> int:
    return get(chat_id).get("turns", 0)
