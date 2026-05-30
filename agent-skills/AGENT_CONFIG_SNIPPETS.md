# Agent discovery — config snippets

How to point each coding agent at the **shared** skill directory:

```
c:\Users\Пользователь\OneDrive\Документы\claude-agents\agent-skills
```

> These are **proposed** snippets. Review before applying — do not blindly overwrite existing agent config.
> The canonical cross-agent installer is the Vercel `skills` CLI (see the `agent-skills-cli` skill); it knows the
> native skill dir for 50+ agents and can `--copy` or symlink into each. Prefer it when an agent is supported.

---

## Claude Code (this environment) — already active

Claude Code auto-discovers skills in:
- **User scope:** `~/.claude/skills/` → `C:\Users\Пользователь\.claude\skills` (all 9 skills installed here = Cloud AI target)
- **Project scope:** `<repo>/.claude/skills/` (this repo's own 14 skills live here)

No config needed — drop a `SKILL.md` folder in either path and it loads by `description`. The shared
`./agent-skills` dir is an extra portable copy; to also expose it to Claude Code, symlink or copy folders into
`~/.claude/skills`, or run `npx skills add <repo> --agent claude-code`.

## Cursor

Cursor reads project rules from `.cursor/rules/`. Point it at the shared skills by referencing them, or copy:
```bash
npx skills add vercel-labs/agent-skills --agent cursor
# or manual: copy agent-skills/<skill>/SKILL.md into .cursor/rules/<skill>.md
```

## Codex (OpenAI) CLI

Codex reads `AGENTS.md` at repo root. Add a pointer:
```markdown
## Skills
Reusable skill playbooks live in ./agent-skills/<name>/SKILL.md. Read the relevant SKILL.md before related work.
```
Or: `npx skills add <org>/<repo> --agent codex`

## Gemini CLI

Gemini CLI reads `GEMINI.md` (and `.gemini/`). Add the same pointer block as Codex, or:
```bash
npx skills add <org>/<repo> --agent gemini
```

## OpenCode

OpenCode reads `AGENTS.md` / `.opencode/`. Use the `npx skills` CLI:
```bash
npx skills add <org>/<repo> --agent opencode
```

## Anti-Gravity / other 50+ agents

Use the Vercel CLI which maps each agent to its native dir:
```bash
npx skills add <org>/<repo> --agent '*'      # install to every detected agent
npx skills list --agent '*'                  # see what is detected
```

---

## One-liner: mirror the shared dir into any agent that reads a flat skills folder

```bash
# from repo root, copy every shared skill into a target agent dir
for d in agent-skills/*/; do cp -a "$d" "<TARGET_AGENT_SKILLS_DIR>/"; done
```
