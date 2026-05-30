---
name: agent-skills-cli
description: Use when installing, updating, removing, or listing Agent Skills from a GitHub (or GitLab/git/local) repo across one or many coding agents — Claude Code, Cursor, Codex, Gemini CLI, OpenCode and 50+ tools — via the Vercel "skills" CLI (`npx skills add/remove/list/init`). Trigger on requests like "install this skills repo", "add the vercel-labs skills", "share one skill across Cursor and Claude", "uninstall a skill", "scaffold a new skill", or any "npx skills ..." command.
---

# agent-skills-cli — the `npx skills` installer

`skills` is Vercel's CLI for the open Agent Skills ecosystem. It takes a repo of skills
(folders each containing a `SKILL.md`) and wires them into the skill directories that
coding agents read from — so one canonical copy is shared across Claude Code, Cursor,
Codex, Gemini CLI, OpenCode, Cline, Continue, Windsurf, GitHub Copilot and 50+ other tools.

- CLI repo: https://github.com/vercel-labs/skills
- Official skills collection: https://github.com/vercel-labs/agent-skills
- Requires **Node.js / npx** (no global install needed — `npx skills ...` fetches and runs it).

## When to use this skill

Reach for it when the user wants to:

- **Install** skills from a GitHub repo into their agent(s): `npx skills add owner/repo`.
- **Share one skill across multiple agents** without copy-pasting (default = symlink to a single source of truth).
- **Update / remove** previously installed skills.
- **Scaffold** a new skill folder: `npx skills init <name>`.
- Choose **project-local vs global (user-level)** scope for where skills land.
- Decide **symlink vs `--copy`** (e.g. when a filesystem or agent does not support symlinks).

If the task is *authoring* a skill's content (writing `SKILL.md`, designing the 3 layers), that is a
different concern — this skill is about the **distribution/install mechanics** via the CLI.

## Command reference (verified from `npx skills --help`)

Top-level commands:

| Command | Purpose |
|---|---|
| `skills add <org/repo>` | Install skills from a source into agent skill dirs |
| `skills remove` | Remove installed skills (interactive when no args) |
| `skills list` | List installed skills |
| `skills init [name]` | Scaffold a new skill folder |
| `skills experimental_sync` | (Experimental) re-sync installed skills with their source |

> The source for `add` accepts GitHub shorthand `owner/repo`. The README also documents full
> URLs, GitLab, raw git URLs, and local paths as sources; treat those as supported but verify
> against `npx skills add --help` if a non-GitHub source is needed.

### `add` options

| Flag | Meaning |
|---|---|
| `-g, --global` | Install at **user level** (`~/<agent>/skills/`) instead of project-local |
| `-a, --agent <agents>` | Target specific agents; pass several space-separated, or `'*'` for **all** detected agents |
| `-s, --skill <skills>` | Install specific skills by name; space-separated, or `'*'` for **all** skills in the repo |
| `-l, --list` | List the skills available in the source **without installing** |
| `-y, --yes` | Skip confirmation prompts |
| `--copy` | **Copy** files instead of symlinking (use when symlinks are unsupported) |
| `--all` | Shortcut for `--skill '*' --agent '*' -y` (everything, every agent, no prompts) |
| `--full-depth` | Discover skills nested outside the standard top-level directories |

### `remove` options

`-g`, `-a <agents>`, `-s <skills>`, `-y`, `--all`. Run `skills remove` with **no args** for an
interactive picker.

### `list` options

`-g`, `-a <agents>`, `--json` (machine-readable output).

## Scope: project vs global

- **Project-local (default):** skills land under the project's per-agent dir, e.g. `./.claude/skills/`
  for Claude Code. Use this when the skill is specific to one codebase and you want it committed/shared
  with the repo and teammates.
- **Global / user-level (`-g`):** skills land under the user home per-agent dir, e.g.
  `~/.claude/skills/`. Use this for skills you want available in **every** project on your machine.

Rule of thumb: project scope for repo-specific workflows; `-g` for personal, cross-project skills.

## Symlink vs `--copy` tradeoff

- **Symlink (default, recommended):** the CLI keeps **one canonical copy** of the skill and symlinks
  each targeted agent's dir to it. A single update propagates to every agent at once — clean, no drift.
- **`--copy`:** writes independent copies into each agent dir. Use when symlinks are not supported
  (some Windows setups without privilege/Developer Mode, certain synced/cloud folders, or agents that
  choke on symlinks). Tradeoff: copies **drift** — updating one does not update the others, and
  `experimental_sync` / re-`add` must touch each copy.

> On Windows, creating symlinks may require Developer Mode or elevated privileges. If `add` fails to
> symlink, retry with `--copy`.

## Multi-agent targeting

- `-a claude-code cursor` → install only to those two agents.
- `-a '*'` → install to **all** agents the CLI detects on the machine/project.
- Omit `-a` → the CLI typically prompts you to choose (use `-y` to accept defaults non-interactively).
- Common agent ids: `claude-code`, `cursor`, `codex`, `gemini` / `gemini-cli`, `opencode`, `cline`,
  `continue`, `windsurf`, `copilot`. If unsure of an exact id, run `skills list -a '*' --json` or check
  `--help`; do not guess an id you are not sure exists.

## Usage recipes

**1. Install the whole official collection, let the CLI prompt for agents:**
```bash
npx skills add vercel-labs/agent-skills
```

**2. Install globally (available in every project on this machine):**
```bash
npx skills add vercel-labs/agent-skills -g
```

**3. Target specific agents only (share across Claude Code + Cursor):**
```bash
npx skills add vercel-labs/agent-skills --agent claude-code cursor
```

**4. Cherry-pick specific skills by name:**
```bash
npx skills add vercel-labs/agent-skills --skill pr-review commit
```
(For the official collection, browse names first with `--list`, e.g. `react-best-practices`,
`web-design-guidelines`, `vercel-optimize`, `vercel-deploy-claimable`.)

**5. Preview before installing, then install everything everywhere unattended:**
```bash
npx skills add vercel-labs/agent-skills --list          # see what's inside, install nothing
npx skills add vercel-labs/agent-skills --all           # = --skill '*' --agent '*' -y
```

**6. Copy instead of symlink (symlink-hostile filesystem / Windows without Dev Mode):**
```bash
npx skills add vercel-labs/agent-skills --agent claude-code --copy -y
```

**7. Remove a skill interactively, or scaffold a new one:**
```bash
npx skills remove                 # interactive picker
npx skills init my-new-skill      # scaffold a SKILL.md folder to author
```

## Operating playbook (recommended order)

1. **Confirm prerequisites:** `node -v` and `npx -v` succeed (Node.js present).
2. **Inspect first:** run `npx skills add <repo> --list` to see what the source offers — never blind-install.
3. **Pick scope:** project (default) vs `-g` (global). Default to project unless the user wants it machine-wide.
4. **Pick agents:** `-a` with explicit ids for a controlled install; `-a '*'` only when truly wanting all.
5. **Pick skills:** `-s name1 name2` to cherry-pick; `-s '*'` (or `--all`) for everything.
6. **Choose mechanism:** symlink (default) unless symlinks are unsupported → `--copy`.
7. **Run, then verify:** `npx skills list` (add `--json` for parsing) to confirm what landed and where.
8. **Maintain:** re-run `add` (or `experimental_sync`) to update; `remove` to uninstall.

## Verification & gotchas

- After install, run `npx skills list` (or `list -a '*' --json`) and confirm the skill appears for the
  intended agent + scope.
- For Claude Code specifically, an installed skill auto-activates by its `description` — confirm the
  installed `SKILL.md` has a precise `description` or it won't trigger.
- If a teammate should get the skill via the repo, install **project-local** (not `-g`) and commit the
  agent's skill dir.
- Symlink install failing on Windows? → `--copy`. Skill not found in source? → re-check with `--list`
  and `--full-depth`. Unknown agent id? → `list --json` / `--help`; do not invent ids.

## Notes on uncertainty

The verified `--help` in this environment lists exactly these commands: `add`, `remove`, `list`,
`init`, `experimental_sync`. The project README additionally mentions `find` and `update` aliases; if
you need those, confirm against the installed CLI version's `--help` before relying on them — behavior
may differ by version. The exact set of supported agent ids should be **verified via `--help` /
`list --json`** rather than assumed.
