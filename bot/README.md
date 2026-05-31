# Local Telegram bot (@TeamCaptainBot) — optional

Питоновский aiogram-бот, который может работать как автономная обёртка над Claude CLI, если плагин Claude Code недоступен. **По умолчанию — НЕ запускать.**

## Критическое предупреждение

`@TeamCaptainBot` используется **одновременно** двумя сущностями:

1. **Claude Code Telegram-плагин** (`plugin:telegram:telegram`) — нативная интеграция, работает в сессии Claude Code через MCP.
2. **Этот Python-бот** (`bot/bot.py`) — stand-alone polling.

Обе сущности вызывают `getUpdates` на одном токене → получаем `409 Conflict: terminated by other getUpdates request` → плагин нестабилен, соединение рвётся.

**Правило:** в один момент времени поллит ТОЛЬКО ОДИН. Выбери сценарий.

## Сценарии

### A. Claude Code запущен (рекомендуется по умолчанию)

- Не запускай `bot.py`.
- В Telegram пишешь напрямую Claude Code через плагин.
- Файлы отправляются через MCP-инструмент `reply(files=[...])`.
- Из любого агента / CLI можно слать файлы через `tools/send_telegram.py` (прямой Bot API, без polling — **не конфликтует** с плагином).

### B. Claude Code НЕ запущен и нужен автономный бот

- Проверь, что нет других процессов с этим токеном:
  ```bash
  tasklist | findstr /I "bun python"
  ```
- Убедись, что плагин Claude Code не спавнит сервер (или закрой Claude Code).
- Запусти `start.bat` или `py bot.py`.

## Отправка файлов без конфликта

Для агентов и скриптов используй `tools/send_telegram.py` — он **только отправляет** (без getUpdates), поэтому никогда не конфликтует с плагином и с этим ботом:

```bash
py tools/send_telegram.py 2061792301 --file C:/path/report.pdf --caption "Отчёт готов"
```

См. `tools/send_telegram.py --help`.

## Архитектура bot.py

- `bot.py` — aiogram 3, handlers для text/photo/document
- `claude_client.py` — обёртка над `claude --print`; на Windows использует shell для запуска `claude.cmd/.exe`
- `config.py` — загрузка `.env` (BOT_TOKEN, CLAUDE_MODEL, ADMIN_IDS, LOG_LEVEL)
- `history.py` — трекер turnов per chat
- регулярка в `bot.py` поддерживает Windows-пути (`C:\\...`, `C:/...`) и Unix (`/...`) с кириллицей — автоматически прикрепляет PDF, упомянутые в ответе Claude

## Почему это осталось

Бот полезен как бэкап: если плагин Claude Code сломан или отключён, можно временно переключиться на автономный режим. Но запускать его параллельно плагину НЕЛЬЗЯ.
