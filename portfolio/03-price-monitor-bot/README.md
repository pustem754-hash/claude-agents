# Price Monitor Bot — Telegram-бот отслеживания цен

aiogram 3.x + aiosqlite + APScheduler. Пользователь кидает ссылку на товар, бот парсит цену и периодически шлёт уведомление при изменении.

## Стек
`Python 3.11+`, `aiogram 3.4`, `aiosqlite`, `APScheduler 3.10`, `requests`, `BeautifulSoup4`, `lxml`, SQLite.

## Поддерживаемые сайты
- **wildberries.ru** — прямой REST API `card.wb.ru` (высокая надёжность)
- **ozon.ru / market.yandex.ru / dns-shop.ru / mvideo.ru / citilink.ru** — специфичные CSS-селекторы
- **любой другой** — универсальный fallback на `itemprop=price`, `data-price`, `og:price:amount`

## Архитектура
```
price-monitor-bot/
├── main.py               # инициализация бота + БД + планировщика
├── config.yaml
├── requirements.txt
├── src/
│   ├── bot.py            # хендлеры /start /add /list /remove + FSM + inline-кнопки
│   ├── database.py       # aiosqlite: products + price_history
│   ├── scraper.py        # WB API + CSS-селекторы + универсальный fallback
│   └── scheduler.py      # APScheduler AsyncIOScheduler
└── data/bot.sqlite
```

## БД
`products(id, user_id, url, name, current_price, last_price, check_interval, created_at, last_checked)` — UNIQUE по `(user_id, url)`.
`price_history(id, product_id, price, recorded_at)` — CASCADE DELETE.

## Команды
| Команда | Действие |
|---------|---------|
| `/start` | Приветствие + список команд |
| `/add` | FSM: запрашивает URL → парсит цену → сохраняет |
| `/list` | Список отслеживаемых товаров |
| `/remove` | Inline-кнопки для удаления |
| `/help` | Справка |

## Уведомления
Каждые `CHECK_INTERVAL_MINUTES` (по умолчанию 30) планировщик обходит все товары, сравнивает цену, пишет историю и шлёт пользователю сообщение с дельтой в рублях и процентах.

## Запуск
```bash
pip install -r requirements.txt
cp .env.example .env          # вставить BOT_TOKEN
python main.py

# в продакшене
pm2 start main.py --name price-bot --interpreter python3 && pm2 save
```

## Безопасность
`BOT_TOKEN` живёт только в `.env` на сервере. `.env` в `.gitignore`. Утёк токен — немедленно `/revoke` у @BotFather.
