# News Parser — парсер российских новостных сайтов с RabbitMQ

Production-ready система автоматического сбора статей. Модульная, конфигурируется через YAML, имеет четыре стратегии получения HTML и умеет обходить CloudFlare / ServicePipe / жёсткие anti-bot системы.

## Стек
`Python 3.10+` · `pika + RabbitMQ 3.13` · `cloudscraper` · `playwright 1.58 + Chromium` · `tf-playwright-stealth` · `FlareSolverr` · `lxml` · `PyYAML` · `Docker`

## Архитектура fetch-слоя

`src/scraper.py::fetch()` выбирает стратегию загрузки страницы по флагам из `config/sites.yaml`:

| Приоритет | Флаг | Fetcher | Когда использовать |
|-----------|------|---------|---------------------|
| 1 | `use_flaresolverr: true` | FlareSolverr (Docker, http://host:8191/v1) | CloudFlare-капчи, ServicePipe с RU-IP |
| 2 | `use_playwright: true` | Headless Chromium + ручной stealth-JS + storage_state | JS-challenge, SPA, сайты с жёсткой IP-фильтрацией |
| 3 | `use_playwright: true`+`use_stealth: true` | То же + tf-playwright-stealth | Только для сайтов, где ручного stealth недостаточно. **Осторожно — может ломать загрузку** (см. ниже) |
| 4 | `cloudflare: true` | cloudscraper | Базовый обход CloudFlare CAPTCHA-challenge |
| 5 | (default) | plain `requests` | Сайты без anti-bot |

### Per-site прокси
В YAML каждого сайта можно указать:
```yaml
proxy: "${TASS_PROXY:-}"
```
Подстановка переменных `${VAR}` и `${VAR:-default}` берёт значение из `.env` на сервере. **В YAML коммитить только имя переменной**, никогда не настоящий адрес с логином.

### storage_state для Playwright
Cookies, установленные сайтом после прохождения JS-challenge, сохраняются в `.playwright_state/<site_key>.json` и автоматически переиспользуются при следующем запуске. Это экономит 2–5 секунд на запрос (не нужно снова проходить challenge) и делает поведение неотличимым от возвращающегося пользователя. Пример: RBC после первого запроса положил 97 cookies — следующие запросы стартуют сразу с авторизованной сессии.

### ⚠️ Про `use_stealth: true`
Пакет `tf-playwright-stealth` добавляет патчи для WebGL, canvas, audio, WebRTC. На одних сайтах он помогает пройти fingerprint-проверки, но **на rbc.ru ломает загрузку полностью** — сервер в ответ отдаёт 39-байтную заглушку вместо статьи. Поэтому флаг включается точечно, по сайтам, где реально помогает (обычно это TASS с RU-прокси и некоторые защищённые e-commerce).

## Архитектура pipeline
```
Producer (scripts/producer.py) --enqueue--> [news_urls] (RabbitMQ)
                                              |
                                              v
                                          Consumer (scripts/consumer.py)
                                              |
                                    +---------+---------+
                                    |                   |
                               [news_articles]    [news_errors]
```
- `src/queue.py` — producer/consumer поверх pika: durable queues, persistent messages, prefetch=1, автопереподключение, NACK-в-DLQ
- `src/parser.py` — XPath-парсер по `config/sites.yaml`, валидация `title + text >= 100 символов`
- `src/scraper.py` — описан выше

## Установка
```bash
pip install -r requirements.txt
playwright install chromium

cp .env.example .env                  # BOT_TOKEN, RU-прокси (опц.)
docker compose up -d rabbitmq         # всегда
docker compose up -d flaresolverr     # если нужен обход CloudFlare/ServicePipe
```

## Быстрый тест парсера
```bash
python scripts/test_parser.py --site lenta_ru --url https://lenta.ru/news/2026/04/13/blockade/
python scripts/test_parser.py --site rbc_ru  --url https://www.rbc.ru/business/15/04/2026/...
python scripts/test_parser.py --site tass_com --url https://tass.com/politics/2117115
```

## Поддерживаемые сайты (config/sites.yaml)

| Сайт | Fetcher | Стабильность |
|------|---------|--------------|
| `lenta_ru` | cloudscraper | ✅ Работает из любой геолокации |
| `rbc_ru`   | Playwright (stealth OFF) | ✅ Работает из любой геолокации благодаря Playwright |
| `tass_ru`  | Playwright + (опционально) RU-proxy | ⚠️ Требует RU-IP — ServicePipe блокирует по ASN/geo |
| `tass_com` | requests | ✅ Англоязычное зеркало TASS без ServicePipe |

Добавление нового сайта = новая секция в YAML (title/text/author/date XPath-ы + флаги fetcher-а). Правок кода не требуется.

## Production-запуск
```bash
python scripts/consumer.py              # воркер (читает news_urls, пишет в news_articles/news_errors)
python scripts/producer.py --demo       # тестовое наполнение очереди
python scripts/producer.py --status     # статистика очередей
```

## Безопасность
- `.env` в `.gitignore` — никаких токенов в коммитах
- `.playwright_state/` в `.gitignore` — cookies могут содержать session-токены
- `proxy: "${TASS_PROXY}"` в YAML — адрес прокси живёт только в `.env` на сервере
- Secrets, затёкшие в историю, немедленно отзываются и ротируются

## Артефакты в папке
- `technical_description.pdf` — техническое описание v1.0
- `test_results_local.txt` — свежие результаты прогона test_parser.py на 4 сайтах
- `test_results.txt` / `examples.json` — сохранённые выходы демо-прогонов
- `parser_demo_log.txt` — лог producer/consumer
- `rabbitmq_queues_screenshot.png` — скриншот management UI с тремя очередями
