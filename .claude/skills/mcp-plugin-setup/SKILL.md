---
name: mcp-plugin-setup
description: >-
  Установка и подключение в Claude Code: плагины из маркетплейсов, MCP-серверы
  (в т.ч. с API-ключом или OAuth), наборы скиллов из репо, CLI-утилиты. Брать,
  когда пользователь просит "поставь плагин", "подключи MCP", "добавь
  firecrawl/morph/higgsfield/exa", "вставь эти N плагинов", "настрой
  маркетплейс" или прислал ссылку на плагин/MCP/skills-репо. Гарантирует
  secret-safe подключение (секреты не попадают в git).
---

# Установка плагинов и MCP в Claude Code

Цель: довести до **рабочего** состояния (connected/enabled), без дублей и без
секретов в git. Сначала инвентаризация, потом классификация источника, потом
установка, потом проверка.

## Шаг 1. Инвентаризация (НЕ ставить дубли)

```
claude plugin list                 # что уже стоит (enabled/disabled)
claude plugin marketplace list     # какие маркетплейсы подключены
claude mcp list                    # какие MCP уже есть + статус коннекта
```
Плюс прочитать `.mcp.json` в корне проекта. Если запрошенное уже есть — сказать
и не переустанавливать. Многие "плагины из подборок" уже идут внутри
`everything-claude-code` / `oh-my-claudecode` (Exa, codex, frontend-design,
skill-creator и т.д.) — сверяйся, прежде чем тащить отдельно.

## Шаг 2. Классификация источника

| Тип | Признак | Установка |
|-----|---------|-----------|
| **CC-плагин** | в репо есть `.claude-plugin/marketplace.json` | `claude plugin marketplace add <owner/repo>` → `claude plugin install <name>@<marketplace>` |
| **Официальный плагин** | claude.com/plugins/... | маркетплейс `claude-plugins-official` обычно уже есть → `claude plugin install <name>@claude-plugins-official` |
| **MCP-сервер** | URL `/mcp` или npm-пакет `*-mcp` | secret-safe add — см. `tools/add_mcp_server.ps1` |
| **skills-репо** | `npx skills add ...`, есть `SKILL.md` в подпапках | поставить ТОЛЬКО нужные SKILL.md (не `--all` — раздувает контекст) |
| **CLI-утилита** | "дашборд", "запусти в терминале" | `npm i -g <pkg>`, дальше отдельная команда |

Имя плагина в маркетплейсе ≠ имя репо. Проверь манифест:
`cat ~/.claude/plugins/marketplaces/<mp>/.claude-plugin/marketplace.json`.

## Шаг 3. MCP-серверы — secret-safe (КРИТИЧНО)

Секрет НИКОГДА не в git-tracked `.mcp.json`. Два валидных пути:

1. **User-scope (проще, не трекается git)** — ключ живёт в `~/.claude.json`:
   ```
   claude mcp add --scope user <name> -e KEY=<value> -- npx -y <pkg>
   ```
2. **Tracked `.mcp.json` + env** — в файле только `${KEY}`, значение в env:
   ```
   setx KEY "<value>"          # Windows user-env; нужен НОВЫЙ процесс
   # в .mcp.json: "env": { "KEY": "${KEY}" }
   ```
   После `setx` Claude Code увидит переменную только после перезапуска.

Запусти `tools/add_mcp_server.ps1`, он закрывает оба случая идемпотентно.

- **Ключ в URL не класть** (утечёт в логи прокси/CDN). Только `-e` / header / env.
- **OAuth-MCP** (Higgsfield `mcp.higgsfield.ai/mcp`, legalzoom): добавить URL как
  `--transport http`, ключ не нужен — пользователь авторизуется при первом
  вызове (`/mcp` → браузер).
- Источники ключей: Firecrawl `firecrawl.dev/app/api-keys`,
  Morph `morphllm.com/dashboard/api-keys`.

## Шаг 4. skills-репо

```
npx -y skills@latest add <owner/repo> -l     # список доступных скиллов
```
Затем поставить нужные **поштучно** копированием в `~/.claude/skills/`:
склонировать репо, `cp -r <repo>/.../<skill> ~/.claude/skills/<skill>`. Проверить,
что в `SKILL.md` есть `name:` и `description:` — иначе Claude Code не подцепит.
Глобальный режим CLI кладёт в `~/.agents/skills/` — Claude Code это НЕ читает.

## Шаг 5. Проверка (обязательно)

```
claude plugin list | grep enabled
claude mcp list                  # каждый нужный сервер = ✓ Connected (или ! Needs auth для OAuth)
```
Сказать пользователю: **перезапустить Claude Code** — подхватит команды новых
плагинов, скиллы и env-переменные. Для OAuth-MCP — авторизоваться через `/mcp`.

## Шаг 6. Итог пользователю

Таблица: что поставлено / что было / что ждёт ключ. Для ждущих ключ — точная
команда (`setx ... ; pwsh tools/...`). Назвать узкие места (дубли, ручные шаги).

## Подводные камни (проверено)

- `claude plugin marketplace add` падает на репо без `marketplace.json` — это
  skills-репо или CLI, не плагин. Не настаивай.
- `pwsh` в окружении может не быть → `powershell -ExecutionPolicy Bypass -File ...`.
- Параллельные `claude`-процессы пишут общий конфиг → ставь плагины
  последовательно, не в parallel.
- `npx skills add -s 'a,b'` через запятую может не распознать → отдельные `-s`
  или ручное копирование (надёжнее).

Готовый рецепт на типовую подборку и точные команды — `tools/recipes.md`.
