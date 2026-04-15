# News Parser — парсер российских новостных сайтов с RabbitMQ

Модульная production-ready система автоматического сбора статей с новостных сайтов (lenta.ru, rbc.ru, tass.ru).
Обходит CloudFlare, работает по схеме producer/consumer поверх RabbitMQ, конфигурация сайтов — в YAML.

## Стек
`Python 3.10+`, `cloudscraper`, `lxml`, `pika`, `PyYAML`, `requests`, `RabbitMQ 3.13`, `Docker`.

## Архитектура
```
Producer (scripts/producer.py) --enqueue--> [news_urls]
                                              |
                                              v
                                          Consumer (scripts/consumer.py)
                                              |
                                    +---------+---------+
                                    |                   |
                               [news_articles]    [news_errors]
```
- **src/scraper.py** — HTTP-клиент, cloudscraper для сайтов за CloudFlare, ротация UA, rate limit 6–12 сек, retry x3 с backoff.
- **src/parser.py** — XPath-парсер, селекторы из `config/sites.yaml`, валидация `title + text >= 100 символов`.
- **src/queue.py** — producer/consumer поверх pika: durable-очереди, persistent messages, prefetch=1, автопереподключение, NACK-в-DLQ.
- **src/models.py** — dataclass-ы `ParseTask`, `Article`, `ParseError` с JSON-сериализацией.

## Запуск
```bash
pip install -r requirements.txt
cp .env.example .env
docker-compose up -d              # RabbitMQ на :5672, UI на :15672 (guest/guest)

python scripts/test_parser.py --site lenta_ru --url https://lenta.ru/news/...
python scripts/consumer.py        # в одном терминале — воркер
python scripts/producer.py --demo # в другом — наполнение очереди
python scripts/producer.py --status
```

## Добавление нового сайта
Править только `config/sites.yaml` — добавить секцию с XPath-селекторами `title / text / author / date` и флагом `cloudflare`. Перезапустить consumer.

## Артефакты в папке
- `technical_description.pdf` — техническое описание прототипа v1.0.
- `test_results.txt` — результаты прогонов парсера.
- `examples.json` — примеры распарсенных статей.
- `parser_demo_log.txt` — лог демо-запуска.
- `rabbitmq_queues_screenshot.png` — скриншот панели RabbitMQ с тремя очередями.
