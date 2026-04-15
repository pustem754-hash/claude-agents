# Catalog Parser — парсер каталогов товаров (WB / Ozon / универсальный HTML)

Три режима работы в одном CLI: API Wildberries, Playwright для Ozon (JS-рендеринг) и универсальный HTML-парсер по CSS-селекторам. Новый сайт добавляется YAML-конфигом без правок кода.

## Стек
`Python 3.11+`, `requests`, `BeautifulSoup4`, `lxml`, `Playwright + Chromium`, `PyYAML`, `pandas`.

## Структура
```
catalog-parser/
├── main.py
├── config/{wildberries,ozon,generic_example}.yaml
├── src/
│   ├── parser.py            # оркестратор, выбор адаптера
│   ├── fetcher.py           # HTTP: retry, backoff, rate limit, ротация UA, proxy
│   ├── exporters.py         # CSV (UTF-8 BOM) + JSON
│   └── adapters/
│       ├── wildberries.py   # search.wb.ru API
│       ├── ozon.py          # Playwright + scroll/click
│       └── html_parser.py   # универсальный BeautifulSoup
└── output/
```

## Собираемые поля
`id, name, brand, price, original_price, image, url, availability, rating, reviews`.

## Запуск
```bash
pip install -r requirements.txt
playwright install chromium           # только для режима playwright

python main.py --config wildberries --query "ноутбук"
python main.py --config ozon
python main.py --config /path/to/mysite.yaml --output ./results
python main.py --all
```

## Форматы вывода
- **CSV** с UTF-8 BOM — открывается в Excel/Sheets без кракозябр.
- **JSON** вида `{"total": N, "products": [...]}` — удобно для пайплайнов.

## Замечания
WB и Ozon активно защищаются от парсинга. При частых запросах возможна временная блокировка по IP — используйте residential proxy через `HTTP_PROXY` в `.env`.
