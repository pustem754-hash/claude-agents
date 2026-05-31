"""Bot configuration loaded from environment."""
import os
from pathlib import Path
from dotenv import load_dotenv

BOT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = BOT_DIR.parent

load_dotenv(BOT_DIR / ".env")
load_dotenv(PROJECT_DIR / ".env", override=False)


def _require(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Environment variable {name} is required")
    return v


BOT_TOKEN = _require("BOT_TOKEN")

# На Windows claude CLI обычно доступен как `claude` (shim из npm/claude-code) или
# `claude.cmd`. Дефолт `claude` работает если каталог есть в PATH.
CLAUDE_CLI = os.getenv("CLAUDE_CLI", "claude")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "sonnet")
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "1800"))
CLAUDE_EXTRA_ARGS = [
    a for a in os.getenv("CLAUDE_EXTRA_ARGS", "").split() if a
]

SYSTEM_PROMPT_PATH = Path(os.getenv("SYSTEM_PROMPT_PATH", PROJECT_DIR / "CLAUDE.md"))

HISTORY_DIR = BOT_DIR / "data"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

MAX_MESSAGE_LEN = 4000

ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
