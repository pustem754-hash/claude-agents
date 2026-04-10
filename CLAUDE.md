# Claude Code Toolkit — Agent Teams

Универсальный тулкит из 8 агентов для Claude Code Agent Teams. Каждый агент заточен под конкретный класс задач. Можно вызывать напрямую или через Router.

## Обязательный режим запуска

Запуск через `tmux` обязателен для Agent Teams.

```bash
tmux new -s claude-toolkit
claude
```

## Обязательные настройки проекта

В `.claude/settings.json` должно быть:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "tmux"
}
```

## Агенты

| # | Агент | Назначение | Модель | MCP (опционально) |
|---|-------|-----------|--------|-------------------|
| 1 | `router` | Lead-агент, маршрутизация запросов и цепочки | opus | — |
| 2 | `deep-research` | Глубокий ресёрч по любой теме | opus | Brave Search |
| 3 | `parser` | Парсинг сайтов в таблицу | sonnet | Chrome DevTools, Google Sheets |
| 4 | `news-digest` | Дайджест новостей по темам | sonnet | Brave Search |
| 5 | `doc-analyzer` | Анализ документов любого формата | opus | — |
| 6 | `report-generator` | Генерация отчётов из данных | sonnet | Google Sheets |
| 7 | `meeting-notes` | Обработка транскриптов встреч | sonnet | Google Sheets |
| 8 | `youtube-analyzer` | Анализ YouTube видео: скачивание, транскрибация, выжимка | opus | — |

## Два режима работы

### Прямой вызов агента

Пользователь запускает конкретного агента:
Создай Team с агентом deep-research.
Тема: "Лучшие ноутбуки для разработки 2026"

### Через Router

Пользователь описывает задачу, Router выбирает агента(ов):
Создай Agent Team с router.
Задание: "Спарси вакансии с HH и сделай отчёт по зарплатам"

Router определит цепочку: parser → report-generator
Создай Agent Team с router.
Задание: "Проанализируй это видео и сделай отчёт: https://youtube.com/watch?v=..."

Router определит цепочку: youtube-analyzer → report-generator

## MCP-зависимости

Агенты проверяют наличие MCP при старте. Если MCP не установлен:
1. Агент предлагает установку с пошаговой инструкцией
2. Если пользователь отказывается — агент работает через fallback

| MCP | Используется в | Fallback |
|-----|---------------|----------|
| Brave Search | deep-research, news-digest | WebSearch + WebFetch |
| Chrome DevTools | parser | WebFetch (только статический HTML) |
| Google Sheets | parser, report-generator, meeting-notes | CSV/XLSX файлы |
| yt-dlp + whisper + ffmpeg | youtube-analyzer | — (обязательны) |

## Runtime-структура
agent-runtime/
├── shared/        # Промежуточные данные (для цепочек агентов)
├── outputs/       # Финальные результаты
└── state/         # Статус работы

## Роли агентов

Детальные описания: `.claude/agents/`
