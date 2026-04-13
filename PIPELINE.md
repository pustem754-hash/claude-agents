# Pipeline — YouTube Outlier Analysis

Pipeline для поиска вирусных/выделяющихся видео на YouTube по AI-тематике.
Использует реальных агентов из `.claude/agents/`.

## Цепочка

| # | Агент | Что делает | Артефакт |
|---|-------|-----------|----------|
| 1 | `router` | Lead, классифицирует запрос, запускает цепочку, собирает итог | plan.md |
| 2 | `parser` | Парсит YouTube (Chrome DevTools MCP / WebFetch / Apify API) | `agent-runtime/shared/raw-data.json` |
| 3 | `deep-research` | Фильтрует видео, считает Outlier Score, подтягивает контекст | `agent-runtime/shared/outliers.json` |
| 4 | `transcript-analyst` | Скачивает субтитры через Supadata MCP, делает маркетинговый разбор топ-15 | `agent-runtime/shared/transcript-analysis.json` |
| 5 | `report-generator` | Пишет Google Sheet + PDF/HTML отчёт | `agent-runtime/outputs/report.pdf`, Google Sheet |

## Поток данных

`router → parser → deep-research → transcript-analyst → report-generator → router`

Каждый агент по завершении:
1. Сохраняет файл в `agent-runtime/shared/`
2. Отправляет SendMessage следующему с кратким саммари

## Логика фильтрации (deep-research)

Пороги для отбора outlier-видео:
- Минимум 15 000 просмотров
- Максимум 2M подписчиков канала (отсечь гигантов)
- Outlier Score = `views / channel_avg_views` ≥ 2.0x
- Свежесть: не старше 21 дня

## Логика разбора (transcript-analyst)

Для каждого из топ-15 видео:
- Хук (первые 30 сек)
- Формат (туториал, обзор, сравнение, storytelling, реакция)
- Главный тезис, ключевые слова, целевая аудитория
- Почему стал outlier (гипотеза)
- Реплицируемость (high/medium/low)

## Финальный артефакт

- Google Sheet с 4 листами: EN outliers, RU outliers, Dashboard (графики), маркетинговый анализ
- PDF/HTML-отчёт в `agent-runtime/outputs/`
- Брифинг от `router` в `agent-runtime/outputs/briefing.md`

## Внешние зависимости

Переменные окружения (см. `.env.example`):
- `BRAVE_API_KEY` — поиск (deep-research, news-digest)
- `SUPADATA_API_KEY` — транскрипты (transcript-analyst)
- `APIFY_TOKEN` — парсинг YouTube (опционально, альтернатива Chrome DevTools MCP)

MCP-серверы:
- `brave-search` — Web/News/Video поиск
- `supadata` — транскрипты YouTube
- `chrome-devtools` (опц.) — JS-rendered парсинг
- `googlesheets` (опц.) — запись отчёта
