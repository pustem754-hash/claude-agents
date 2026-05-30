# Agent Skills — Install Manifest

**Date:** 2026-05-31
**Environment:** Windows 11 Pro (10.0.26200), Claude Code (Opus 4.8), git-bash shell.
**Tooling present:** node v24.11.1 · npm 11.6.2 · npx 11.6.2 · git 2.52.0 · python 3.10.11

> **Environment note.** The source prompt assumed a Linux/macOS "Cloud Cowork / Cloud AI" box. This machine is
> **Windows Claude Code**. The "Cloud AI / Cloud Cowork skill directory used by the current assistant" was mapped
> to the **Claude Code user skill directory** (the dir the active assistant actually auto-loads). The shared
> code-agent directory is a project-local `./agent-skills` folder, per the prompt's default.

## Detected directories

| Role | Path |
|------|------|
| **Cloud AI / active-assistant skill dir** | `C:\Users\Пользователь\.claude\skills` |
| **Shared code-agent skill dir** | `C:\Users\Пользователь\OneDrive\Документы\claude-agents\agent-skills` |
| (project skill dir, pre-existing, untouched) | `C:\Users\...\claude-agents\.claude\skills` (user's own 14 skills) |
| Clone staging (sources) | `C:\Users\...\claude-agents\tmp\skill-src` |

## Installed skills

| # | Skill | Source | Install method | SKILL.md | Both dirs |
|---|-------|--------|----------------|----------|-----------|
| 1 | frontend-design | https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design | copied from local Anthropic plugin install | yes 4482 B | yes |
| 2 | web-design-guidelines | https://github.com/vercel-labs/agent-skills | cloned repo | yes 1270 B | yes |
| 3 | shadcn-ui | https://ui.shadcn.com/docs/skills | authored from official docs (web research) | yes 11595 B | yes |
| 4 | superpowers | https://github.com/obra/superpowers-skills (+ obra/superpowers) | cloned 31-skill bundle + authored root index | yes 8795 B | yes |
| 5 | react-best-practices | https://github.com/vercel-labs/agent-skills | cloned repo | yes 7400 B | yes |
| 6 | postgres-best-practices | https://mcpservers.org/agent-skills/supabase/postgres-best-practices (Supabase) | authored from research | yes 16991 B | yes |
| 7 | mcp-builder | https://github.com/anthropics/skills | copied from local Anthropic skills install | yes 9328 B | yes |
| 8 | canvas-design | https://github.com/anthropics/skills (ComposioHQ listing) | copied from local Anthropic skills install | yes 12068 B | yes |
| 9 | agent-skills-cli | https://github.com/vercel-labs/skills | authored from verified `npx skills --help` | yes 8730 B | yes |

**Result: 9/9 skills installed into both directories. 0 failed.**

### superpowers bundle detail
`superpowers/skills/` contains **31 sub-skills** (categories: architecture, collaboration, debugging, meta,
problem-solving, research, testing, using-skills) from `obra/superpowers-skills`. The root `superpowers/SKILL.md`
is an authored index. Headline workflows: `collaboration/brainstorming`, `collaboration/writing-plans`,
`collaboration/executing-plans`, `debugging/systematic-debugging`, `testing/test-driven-development`.

## Failures / partials
- **None for install coverage.** All 9 skills present + non-empty in both dirs.
- One cosmetic workflow event: the superpowers-index authoring agent wrote its file but did not emit a
  StructuredOutput record; it produced the root SKILL.md in the Cloud dir only. Manually synced to the shared dir
  and verified (8795 B in both). No data lost.

## Backups
Pre-existing folders (if any) were copied to `*.backup.<YYYYMMDD-HHMMSS>` siblings before overwrite. The three
already-present Anthropic skills (frontend-design, mcp-builder, canvas-design) were left in place in the Cloud dir
and additionally copied to the shared dir.

## Next actions (for the user)
1. **Claude Code:** all 9 skills in `~/.claude/skills` auto-load by `description` — already visible in the skill
   registry (shadcn-ui, postgres-best-practices, agent-skills-cli, superpowers, etc.). No activation step needed.
2. **superpowers slash commands** (`/brainstorm`, `/write-plan`, `/execute-plan`) require installing the
   **obra/superpowers plugin**, not just the skills bundle: `/plugin marketplace add obra/superpowers-marketplace`
   then `/plugin install superpowers`. The skills here give the playbooks; the plugin wires the commands.
3. **Other agents (Cursor/Codex/Gemini/OpenCode/…):** see `AGENT_CONFIG_SNIPPETS.md` or run
   `npx skills add <org>/<repo> --agent '*'`.
4. **Repo hygiene:** consider gitignoring `tmp/` and `*.backup.*`. Decide whether `agent-skills/` should be
   committed (portable shared skills) or ignored.
5. **Cleanup (optional):** the source clones in `tmp/skill-src` can be deleted once satisfied.

## Verify commands
```bash
# every SKILL.md in both targets
find "/c/Users/Пользователь/.claude/skills" -maxdepth 2 -name SKILL.md
find "/c/Users/Пользователь/OneDrive/Документы/claude-agents/agent-skills" -maxdepth 2 -name SKILL.md
# byte sizes (non-empty check)
for s in frontend-design web-design-guidelines shadcn-ui superpowers react-best-practices postgres-best-practices mcp-builder canvas-design agent-skills-cli; do \
  wc -c "agent-skills/$s/SKILL.md"; done
```
