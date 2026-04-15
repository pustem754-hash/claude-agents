# Портфолио — парсинг, очереди, Telegram-боты

Привет. Я Python-разработчик, специализируюсь на автоматизации сбора данных и ботах. В этом портфолио — три законченных проекта, которые я собрал как production-ready прототипы: исходный код, документация, логи прогонов и скриншоты.

## Что я умею
- **Парсинг сайтов** — новости, каталоги товаров, карточки с ценами. Обход CloudFlare через `cloudscraper`, JS-рендеринг через Playwright, универсальные парсеры по CSS/XPath-селекторам.
- **Очереди сообщений** — RabbitMQ: durable-очереди, persistent messages, DLQ, prefetch=1, автопереподключение, retry с экспоненциальным backoff.
- **Telegram-боты** — `aiogram 3.x`, FSM, inline-клавиатуры, планировщик задач (`APScheduler`), уведомления.
- **Хранение данных** — SQLite (aiosqlite), CSV/JSON-экспорт, UTF-8 BOM для Excel.
- **Инженерная гигиена** — Python 3.10+, Docker / docker-compose, конфигурация через YAML и `.env`, `.gitignore`, README и техописание к каждому проекту.

## Проекты

### 01. [News Parser](./01-news-parser/) — парсер новостных сайтов с RabbitMQ
Producer/consumer система для сбора статей с `lenta.ru`, `rbc.ru`, `tass.ru`. CloudFlare обходится через `cloudscraper`, статьи валидируются и публикуются в отдельные очереди `news_articles` / `news_errors`. Новый сайт добавляется через YAML без правок кода.

Стек: `Python 3.10+`, `cloudscraper`, `lxml`, `pika`, `PyYAML`, `RabbitMQ 3.13`, `Docker`.

### 02. [Catalog Parser](./02-catalog-parser/) — парсер каталогов товаров
Один CLI, три режима: Wildberries через публичный API, Ozon через Playwright (JS-рендеринг и скроллинг), универсальный HTML-парсер по CSS-селекторам для любого другого магазина. Экспорт в CSV (UTF-8 BOM) и JSON.

Стек: `Python 3.11+`, `requests`, `BeautifulSoup4`, `lxml`, `Playwright + Chromium`, `PyYAML`.

### 03. [Price Monitor Bot](./03-price-monitor-bot/) — Telegram-бот мониторинга цен
Пользователь кидает ссылку на товар — бот сохраняет в SQLite, раз в 30 минут проверяет цену через `APScheduler` и шлёт уведомление, если цена изменилась. Поддерживает WB, Ozon, Yandex.Market, DNS, М.Видео, Citilink + универсальный fallback на `itemprop=price`.

Стек: `Python 3.11+`, `aiogram 3.4`, `aiosqlite`, `APScheduler`, `BeautifulSoup4`, SQLite.

## Как связаться
В каждой папке лежит отдельный README и `technical_description.pdf` / `*-docs.pdf`. Сводная PDF по всему портфолио — `portfolio-summary.pdf`.
