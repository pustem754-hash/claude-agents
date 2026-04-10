# Agent Runtime
Рабочая директория для Claude Code Toolkit агентов.
## Структура
- `shared/` — промежуточные данные между агентами (для цепочек)
- `outputs/` — финальные результаты работы агентов
- `state/` — статус текущей работы
- `messages/` — handoff-сообщения между агентами
## Очистка
Для очистки всех данных предыдущих запусков:
```bash
rm -f shared/*.json shared/*.md outputs/*.md outputs/*.pdf outputs/*.csv outputs/*.xlsx outputs/*.png state/*.json state/*.md messages/*.md messages/*.json
```
