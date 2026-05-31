---
name: crm-pipeline
description: >
  Бери этот скилл, когда пользователь ведёт базу клиентов или смотрит воронку:
  «добавь клиента», «покажи клиентов», «обнови статус клиента», «кто в работе»,
  «покажи воронку / pipeline», «сколько hot/warm-лидов», «двинь сделку по этапу»,
  «какой next step у клиента». Делает: CRUD по clients.json (статусы
  new/warm/hot/won/lost, next_step, history) + pipeline-вью hot/warm/cold.
  НЕ для: написания холодных писем, follow-up, КП — это скилл `outreach`.
  НЕ для: поиска заказов на биржах — это скилл `freelance-digest`.
---

# crm-pipeline — база клиентов и воронка продаж

Фокус-скилл: один домен — состояние клиентов и их движение по воронке. Тексты
писем сюда не входят (Правило 3 — не монолит): для outreach/КП есть скилл
`outreach`. Оркестрацию между скиллами берёт на себя вызывающий (зонтик `sales`).

## Когда брать / не брать

- ✅ «Добавь клиента Иван @ivan», «покажи список клиентов», «обнови статус на hot»,
  «покажи воронку», «кто сейчас в работе», «какой next_step у клиента».
- ❌ «Напиши холодное письмо», «сделай follow-up», «собери КП» → `outreach`.
- ❌ «Найди свежие заказы на fl.ru» → `freelance-digest`.

## Хранилище

`agent-runtime/shared/sales/clients.json` — единый JSON-массив записей клиентов.
Схема одной записи — в `tools/clients_schema.json`. Поля: `id`, `name`, `contact`,
`company`, `status`, `source`, `notes`, `next_step`, `created_at`, `updated_at`,
`history[]`.

Статусы (этапы воронки): `new` → `warm` → `hot` → `won` | `lost`.

## Процесс (плейбук)

1. **Все мутации — через `tools/crm.py`**, не правь JSON руками. Скрипт
   детерминированный: читает текущий файл, модифицирует, пишет атомарно, не
   плодит дубли по `contact`, сам проставляет `created_at`/`updated_at`.
2. **Добавить клиента:**
   ```
   python .claude/skills/crm-pipeline/tools/crm.py add \
     --id ivan-petrov --name "Иван Петров" --contact @ivan \
     --status new --source telegram
   ```
   Если `id` не передан — берётся slug от `name`. Дубль по `contact` → скрипт
   откажет, не перезапишет.
3. **Список:** `python .claude/skills/crm-pipeline/tools/crm.py list` —
   человекочитаемая таблица: id, имя, контакт, статус, next_step.
4. **Обновить поле:**
   ```
   python .claude/skills/crm-pipeline/tools/crm.py update \
     --id ivan-petrov --field status --value hot
   ```
   Изменение статуса/next_step пишется и в `history[]` с датой. `updated_at`
   обновляется автоматически.
5. **Воронка:** `python .claude/skills/crm-pipeline/tools/crm.py pipeline` —
   группировка по статусу с разбивкой на hot / warm / cold. Маппинг вью:
   - **hot** ← статус `hot`
   - **warm** ← статус `warm`
   - **cold** ← статусы `new`, `lost` (won показывается отдельным итогом)

## Правила

- Перед любым изменением `clients.json` скрипт читает текущее состояние, чтобы
  не затереть чужие записи. Не обходи скрипт ручным редактированием.
- Не допускай дублей по `contact` — это ключ дедупликации.
- Дату бери фактическую (`datetime.now()`), не из примера.
- Скрипт `crm.py` не переписывай заново при смене формата вывода — правь точечно.
- CRM хранит факты о клиенте. Тексты коммуникаций (письма, КП) тут не живут —
  они генерятся скиллом `outreach` и складываются в `agent-runtime/outputs/sales/`.

## Слои этого скилла

- **tools/crm.py** — детерминированный CLI над clients.json (слой 3, код).
- **tools/clients_schema.json** — JSON-схема записи клиента (слой 3, контракт данных).
- **examples/clients-example.json** — синтетический эталон базы (few-shot, плейсхолдеры @example).
