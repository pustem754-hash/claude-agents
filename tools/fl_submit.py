"""
fl.ru proposal submitter via Chrome DevTools Protocol.

Connects to running Chrome on localhost:9222 (user already logged in).
Opens project URL, clicks "Откликнуться", fills form, takes screenshot.
By default STOPS before sending — requires --send flag to submit.

Usage:
    python tools/fl_submit.py --url https://fl.ru/projects/5501230/...
    python tools/fl_submit.py --url ... --send        # actually submit
    python tools/fl_submit.py --url ... --price 22000 --days 7
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests
import websocket


CDP_HOST = "http://localhost:9222"
DEFAULT_SCREENSHOT = Path("thoughts/fl-submit-preview.png")

DEFAULT_KP = """Здравствуйте!

Опыт 4+ года в разработке торговых ботов на Python (ccxt, binance-connector, python-binance).

Что сделаю:
• Подключение к Binance Spot/Futures API через ccxt
• Реализация стратегии по вашему ТЗ (сетка/трейлинг/индикаторы — уточним при созвоне)
• Risk-management: stop-loss, take-profit, лимиты позиции и дневного убытка
• Логирование сделок в SQLite + Telegram-уведомления о входах/выходах
• Бэктест на исторических данных Binance (1m/5m/1h)
• Деплой на ваш VPS с автозапуском через systemd
• README с инструкцией запуска и конфигом через .env

Стек: Python 3.11, ccxt, pandas, SQLite, docker (по желанию).

Срок: 7 дней с момента согласования ТЗ.
Цена: 22000 руб. фиксированно.

Готов обсудить детали стратегии — пишите в личку или сюда в комментарии."""


class CDPClient:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.msg_id = 0

    def send(self, method: str, params: dict | None = None) -> dict[str, Any]:
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))
        while True:
            raw = self.ws.recv()
            msg = json.loads(raw)
            if msg.get("id") == self.msg_id:
                if "error" in msg:
                    raise RuntimeError(f"CDP error {method}: {msg['error']}")
                return msg.get("result", {})

    def eval_js(self, expr: str, await_promise: bool = False) -> Any:
        res = self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": await_promise,
        })
        if res.get("exceptionDetails"):
            raise RuntimeError(f"JS exception: {res['exceptionDetails']}")
        return res.get("result", {}).get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def get_or_create_target(url: str) -> dict:
    try:
        tabs = requests.get(f"{CDP_HOST}/json/list", timeout=5).json()
    except Exception as e:
        print(f"[ERR] Chrome CDP не отвечает на {CDP_HOST}: {e}")
        print("     Запусти Chrome с --remote-debugging-port=9222")
        sys.exit(2)

    for t in tabs:
        if t.get("type") == "page" and url in t.get("url", ""):
            print(f"[ok] нашёл открытую вкладку: {t['url']}")
            return t

    print(f"[..] открываю новую вкладку: {url}")
    resp = requests.put(f"{CDP_HOST}/json/new?{url}", timeout=10)
    if resp.status_code != 200:
        resp = requests.get(f"{CDP_HOST}/json/new?{url}", timeout=10)
    return resp.json()


def wait_for(client: CDPClient, js_check: str, timeout: float = 15.0, poll: float = 0.4) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if client.eval_js(js_check):
            return True
        time.sleep(poll)
    return False


def click_respond_button(client: CDPClient) -> Any:
    js = r"""
    (() => {
      const all = [...document.querySelectorAll('a,button,input[type=button],input[type=submit]')];
      const btn = all.find(el => {
        const t = (el.innerText || el.value || '').trim().toLowerCase();
        return t.includes('откликнуться') || t.includes('отклик');
      });
      if (!btn) return {found:false};
      btn.scrollIntoView({block:'center'});
      btn.click();
      return {found:true, text: (btn.innerText||btn.value||'').trim(), tag: btn.tagName};
    })()
    """
    return client.eval_js(js)


def fill_form(client: CDPClient, kp_text: str, price: int, days: int) -> dict:
    js = r"""
    (args) => {
      const {text, price, days} = args;
      const setVal = (el, val) => {
        const proto = el.tagName === 'TEXTAREA'
          ? HTMLTextAreaElement.prototype
          : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(el, String(val));
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
      };
      const report = {};

      const tas = [...document.querySelectorAll('textarea')].filter(t => t.offsetParent !== null);
      if (tas.length) {
        setVal(tas[0], text);
        report.textarea = {name: tas[0].name || tas[0].id || '?', len: text.length};
      } else {
        report.textarea = null;
      }

      const inputs = [...document.querySelectorAll('input')].filter(i => i.offsetParent !== null);
      const byHint = (hints) => inputs.find(i => {
        const hay = [i.name, i.id, i.placeholder,
                     (i.labels && i.labels[0] && i.labels[0].innerText) || ''
                    ].join(' ').toLowerCase();
        return hints.some(h => hay.includes(h));
      });

      const priceInp = byHint(['цена','price','стоимост','бюджет','cost']);
      const daysInp  = byHint(['срок','days','день','дней','term']);

      if (priceInp) { setVal(priceInp, price);
        report.price = {name: priceInp.name||priceInp.id||priceInp.placeholder, value: price}; }
      else report.price = null;

      if (daysInp)  { setVal(daysInp, days);
        report.days = {name: daysInp.name||daysInp.id||daysInp.placeholder, value: days}; }
      else report.days = null;

      report.all_inputs = inputs.map(i => ({
        name: i.name, id: i.id, type: i.type,
        placeholder: i.placeholder, value_len: (i.value||'').length
      }));
      return report;
    }
    """
    args_json = json.dumps({"text": kp_text, "price": price, "days": days}, ensure_ascii=False)
    return client.eval_js(f"({js})({args_json})")


def screenshot(client: CDPClient, path: Path) -> Path:
    res = client.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
    data = base64.b64decode(res["data"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def find_submit_button(client: CDPClient) -> Any:
    js = r"""
    (() => {
      const all = [...document.querySelectorAll('button, input[type=submit], a')];
      const btn = all.find(el => {
        const t = (el.innerText || el.value || '').trim().toLowerCase();
        return /отправить|предлож|откликнуться/i.test(t) && el.offsetParent !== null;
      });
      if (!btn) return null;
      return {text:(btn.innerText||btn.value||'').trim(), tag:btn.tagName,
              disabled: !!btn.disabled};
    })()
    """
    return client.eval_js(js)


def click_submit(client: CDPClient) -> dict:
    js = r"""
    (() => {
      const all = [...document.querySelectorAll('button, input[type=submit]')];
      const btn = all.find(el => {
        const t = (el.innerText || el.value || '').trim().toLowerCase();
        return /отправить|предлож/i.test(t) && el.offsetParent !== null && !el.disabled;
      });
      if (!btn) return {ok:false, reason:'no submit button'};
      btn.click();
      return {ok:true, text:(btn.innerText||btn.value||'').trim()};
    })()
    """
    return client.eval_js(js)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="URL заявки fl.ru")
    ap.add_argument("--price", type=int, default=22000)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--text", help="Текст КП (если не указан — DEFAULT_KP)")
    ap.add_argument("--text-file", help="Файл с текстом КП (UTF-8)")
    ap.add_argument("--screenshot", default=str(DEFAULT_SCREENSHOT),
                    help=f"Путь для скриншота (default {DEFAULT_SCREENSHOT})")
    ap.add_argument("--send", action="store_true",
                    help="Реально нажать Отправить (иначе только подготовка+скриншот)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Только проверить подключение/логин, не жать Откликнуться")
    args = ap.parse_args()

    if args.text_file:
        kp_text = Path(args.text_file).read_text(encoding="utf-8")
    elif args.text:
        kp_text = args.text
    else:
        kp_text = DEFAULT_KP

    target = get_or_create_target(args.url)
    ws_url = target["webSocketDebuggerUrl"]
    print(f"[..] подключаюсь к CDP: {ws_url}")

    client = CDPClient(ws_url)
    try:
        client.send("Page.enable")
        client.send("Runtime.enable")

        cur = client.eval_js("location.href")
        if args.url not in (cur or ""):
            print(f"[..] навигация на {args.url}")
            client.send("Page.navigate", {"url": args.url})
            ok = wait_for(client, "document.readyState === 'complete'", timeout=20)
            print(f"[{'ok' if ok else 'warn'}] readyState=complete")

        logged = client.eval_js(
            "!!document.querySelector('.b-username, [class*=\"user-menu\"], [class*=\"profile\"]') "
            "|| /Выйти|Личный кабинет/.test(document.body.innerText)"
        )
        print(f"[{'ok' if logged else 'warn'}] залогинен: {logged}")
        if not logged:
            print("     [!] сессия не похожа на залогиненную. Прерываю.")
            sys.exit(3)

        if args.dry_run:
            print("[ok] dry-run: подключение работает")
            return

        print("[..] ищу кнопку 'Откликнуться'")
        r = click_respond_button(client)
        print(f"     {r}")
        if not (isinstance(r, dict) and r.get("found")):
            print("[!] кнопка 'Откликнуться' не найдена — возможно уже откликнулся или заявка закрыта")
            sys.exit(4)

        print("[..] жду появления формы (textarea)")
        ok = wait_for(client, "document.querySelectorAll('textarea').length > 0", timeout=15)
        if not ok:
            print("[!] форма не появилась за 15с")
            sys.exit(5)
        time.sleep(1.0)

        print("[..] заполняю форму")
        report = fill_form(client, kp_text, args.price, args.days)
        print(f"     textarea: {report.get('textarea')}")
        print(f"     price:    {report.get('price')}")
        print(f"     days:     {report.get('days')}")
        if not report.get("textarea"):
            print("[!] не нашёл textarea для текста КП")
        if not report.get("price"):
            print("[warn] поле цены не матчится эвристикой. Все inputs:")
            for i in report.get("all_inputs", []):
                print(f"       {i}")

        shot = screenshot(client, Path(args.screenshot))
        print(f"[ok] скриншот сохранён: {shot.resolve()}")

        sb = find_submit_button(client)
        print(f"[..] кнопка Отправить: {sb}")

        if not args.send:
            print()
            print("=" * 60)
            print("ФОРМА ЗАПОЛНЕНА. ОТПРАВКА НЕ ВЫПОЛНЕНА.")
            print(f"Скриншот: {shot.resolve()}")
            print("Чтобы отправить — перезапусти с --send")
            print("=" * 60)
            return

        print("[..] жму Отправить")
        res = click_submit(client)
        print(f"     {res}")
        if not res.get("ok"):
            print("[!] не удалось нажать Отправить")
            sys.exit(6)
        time.sleep(2.0)
        shot2 = screenshot(client, Path(args.screenshot).with_stem(Path(args.screenshot).stem + "-after"))
        print(f"[ok] скриншот после отправки: {shot2.resolve()}")

    finally:
        client.close()


if __name__ == "__main__":
    main()
