"""Детерминированный CLI над базой клиентов CRM.

Хранилище: agent-runtime/shared/sales/clients.json (массив записей).
Схема записи: ../tools/clients_schema.json.

Команды:
    add      --id --name --contact [--company --status --source --notes --next-step]
    list
    update   --id --field <поле> --value <значение>
    pipeline

Принципы:
- читать-модифицировать-писать (не затирать чужие записи);
- дедуп по contact (дубль -> отказ);
- created_at/updated_at проставляются автоматически (YYYY-MM-DD, локальная дата);
- смена status/next_step логируется в history[].

Путь к clients.json определяется относительно корня репозитория (4 уровня вверх
от этого файла: tools -> crm-pipeline -> skills -> .claude -> <root>), либо через
переменную окружения CRM_CLIENTS_PATH (используется в тестах).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

VALID_STATUS = ["new", "warm", "hot", "won", "lost"]
VALID_SOURCE = ["telegram", "upwork", "kwork", "fl", "habr", "referral", "other"]
LOGGED_FIELDS = {"status", "next_step"}
EDITABLE_FIELDS = {"name", "contact", "company", "status", "source", "notes", "next_step"}


def clients_path() -> Path:
    env = os.environ.get("CRM_CLIENTS_PATH")
    if env:
        return Path(env)
    root = Path(__file__).resolve().parents[4]
    return root / "agent-runtime" / "shared" / "sales" / "clients.json"


def today() -> str:
    return date.today().isoformat()


_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(name: str) -> str:
    s = "".join(_TRANSLIT.get(ch, ch) for ch in name.strip().lower())
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "client"


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"clients.json должен быть массивом, получено: {type(data).__name__}")
    return data


def save(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_add(args, path: Path) -> None:
    rows = load(path)
    contact = args.contact.strip()
    if any(r.get("contact") == contact for r in rows):
        raise SystemExit(f"Дубль по contact: {contact} — клиент уже есть, отказ.")
    cid = (args.id or slugify(args.name)).strip()
    if any(r.get("id") == cid for r in rows):
        raise SystemExit(f"Дубль по id: {cid} — задай другой --id.")
    status = args.status or "new"
    if status not in VALID_STATUS:
        raise SystemExit(f"status вне {VALID_STATUS}")
    source = args.source or "other"
    if source not in VALID_SOURCE:
        raise SystemExit(f"source вне {VALID_SOURCE}")
    now = today()
    rec = {
        "id": cid,
        "name": args.name,
        "contact": contact,
        "company": args.company or "",
        "status": status,
        "source": source,
        "notes": args.notes or "",
        "next_step": getattr(args, "next_step") or "",
        "created_at": now,
        "updated_at": now,
        "history": [{"date": now, "event": f"created (status: {status})"}],
    }
    rows.append(rec)
    save(path, rows)
    print(f"OK: добавлен {cid} ({args.name}, {contact}) status={status}")


def cmd_list(args, path: Path) -> None:
    rows = load(path)
    if not rows:
        print("CRM пуста.")
        return
    print(f"{'id':<18} {'имя':<22} {'контакт':<18} {'статус':<6} next_step")
    print("-" * 90)
    for r in rows:
        print(f"{r.get('id',''):<18} {r.get('name',''):<22} {r.get('contact',''):<18} "
              f"{r.get('status',''):<6} {r.get('next_step','')}")
    print(f"\nВсего: {len(rows)}")


def cmd_update(args, path: Path) -> None:
    rows = load(path)
    field = args.field
    if field not in EDITABLE_FIELDS:
        raise SystemExit(f"Поле '{field}' нередактируемо. Доступно: {sorted(EDITABLE_FIELDS)}")
    if field == "status" and args.value not in VALID_STATUS:
        raise SystemExit(f"status вне {VALID_STATUS}")
    if field == "source" and args.value not in VALID_SOURCE:
        raise SystemExit(f"source вне {VALID_SOURCE}")
    rec = next((r for r in rows if r.get("id") == args.id), None)
    if rec is None:
        raise SystemExit(f"Клиент id={args.id} не найден.")
    old = rec.get(field, "")
    rec[field] = args.value
    now = today()
    rec["updated_at"] = now
    if field in LOGGED_FIELDS:
        rec.setdefault("history", []).append(
            {"date": now, "event": f"{field}: {old or '∅'} -> {args.value}"}
        )
    save(path, rows)
    print(f"OK: {args.id}.{field}: {old or '∅'} -> {args.value}")


def cmd_pipeline(args, path: Path) -> None:
    rows = load(path)
    buckets = {"hot": [], "warm": [], "cold": [], "won": []}
    view = {"hot": "hot", "warm": "warm", "new": "cold", "lost": "cold", "won": "won"}
    for r in rows:
        buckets[view.get(r.get("status", "new"), "cold")].append(r)
    labels = {"hot": "🔥 HOT", "warm": "🌤 WARM", "cold": "❄ COLD (new/lost)", "won": "✅ WON"}
    for key in ["hot", "warm", "cold", "won"]:
        items = buckets[key]
        print(f"\n{labels[key]} — {len(items)}")
        for r in items:
            ns = r.get("next_step", "")
            print(f"  · {r.get('name','')} ({r.get('contact','')})"
                  + (f" → {ns}" if ns else ""))
    print(f"\nИтого клиентов: {len(rows)}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CRM CLI над clients.json")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="добавить клиента")
    a.add_argument("--id")
    a.add_argument("--name", required=True)
    a.add_argument("--contact", required=True)
    a.add_argument("--company")
    a.add_argument("--status", choices=VALID_STATUS)
    a.add_argument("--source", choices=VALID_SOURCE)
    a.add_argument("--notes")
    a.add_argument("--next-step", dest="next_step")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list", help="список клиентов")
    l.set_defaults(func=cmd_list)

    u = sub.add_parser("update", help="обновить поле клиента")
    u.add_argument("--id", required=True)
    u.add_argument("--field", required=True)
    u.add_argument("--value", required=True)
    u.set_defaults(func=cmd_update)

    pl = sub.add_parser("pipeline", help="воронка hot/warm/cold/won")
    pl.set_defaults(func=cmd_pipeline)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args, clients_path())


if __name__ == "__main__":
    main()
