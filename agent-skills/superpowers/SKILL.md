---
name: superpowers
description: Use when working through any non-trivial engineering task that benefits from a structured, disciplined workflow — brainstorming a rough idea into a design, writing a detailed implementation plan, executing a plan in reviewed batches, debugging systematically to root cause, or building features with test-driven development. This is the ROOT index for the obra/superpowers skill library; it routes you to the right sub-skill under skills/<category>/<name>/SKILL.md. Read this when you are about to start coding/planning/debugging and want the proven workflow instead of improvising.
---

# Superpowers (root index)

A library of proven, reusable engineering workflows packaged as sub-skills. This file is
the **index and router**. The real playbooks live in `skills/<category>/<name>/SKILL.md`.

- Source: https://github.com/obra/superpowers
- Skills source: https://github.com/obra/superpowers-skills
- Library version observed at install: `superpowers` 5.1.0
- 31 sub-skills across 8 categories: architecture, collaboration, debugging, meta,
  problem-solving, research, testing, using-skills.

## Core principle

Skills document proven techniques that save time and prevent known mistakes. **If a
sub-skill matches your situation, you must Read it (the entire file, not just the
frontmatter) and follow it** — do not improvise the workflow from memory. Read first via
`skills/using-skills/SKILL.md` ("Getting Started with Skills") for the mandatory rules.

## How to use this index

1. Identify what phase you are in (idea → design → plan → execute → debug → verify → ship).
2. Find the matching sub-skill in the tables below.
3. Open it with the Read tool using its relative path under this skill folder:
   `skills/<category>/<name>/SKILL.md`. Read the whole file.
4. Announce it: "I've read the [Skill Name] skill and I'm using it to [purpose]."
5. If the sub-skill has a checklist, create a TodoWrite todo for **every** item.

## Headline workflows (the common path)

These five cover the bulk of day-to-day engineering work, in roughly the order you hit them:

| Phase | Sub-skill | Relative path |
|-------|-----------|---------------|
| 1. Brainstorm an idea into a design | Brainstorming Ideas Into Designs | `skills/collaboration/brainstorming/SKILL.md` |
| 2. Write a detailed implementation plan | Writing Plans | `skills/collaboration/writing-plans/SKILL.md` |
| 3. Execute the plan in reviewed batches | Executing Plans | `skills/collaboration/executing-plans/SKILL.md` |
| 4. Debug systematically to root cause | Systematic Debugging | `skills/debugging/systematic-debugging/SKILL.md` |
| 5. Build features test-first | Test-Driven Development | `skills/testing/test-driven-development/SKILL.md` |

The intended flow: **brainstorm → write plan → execute plan**, with **TDD** as the discipline
during execution and **systematic-debugging** when something breaks. Don't skip phases on
"simple" tasks — specific instructions describe *what* to do, not permission to drop the workflow.

### Slash commands — verified status

The obra/superpowers Claude Code plugin (v5.1.0) is designed so **skills trigger automatically
and contextually** — per its README: "Because the skills trigger automatically, you don't need
to do anything special." The only install-time slash command documented is the marketplace
installer:

- `/plugin install superpowers@claude-plugins-official` — install the plugin (Claude Code).

Standalone `/brainstorm`, `/write-plan`, and `/execute-plan` slash commands are **not documented
in the current upstream plugin manifest** (`.claude-plugin/plugin.json`) or README at the time of
this install — status: **unknown / not present in v5.1.0**. To run these workflows here, Read the
mapped sub-skill files directly (paths in the table above) rather than relying on a slash command.
If a future plugin version adds them, they would map: brainstorm → `collaboration/brainstorming`,
write-plan → `collaboration/writing-plans`, execute-plan → `collaboration/executing-plans`.

## Full index by category

### using-skills (read this first)
| Skill | Path |
|-------|------|
| Getting Started with Skills (mandatory workflow, find-skills, announcing usage) | `skills/using-skills/SKILL.md` |

### collaboration (idea → design → plan → execute → review → ship)
| Skill | Path |
|-------|------|
| Brainstorming Ideas Into Designs | `skills/collaboration/brainstorming/SKILL.md` |
| Writing Plans | `skills/collaboration/writing-plans/SKILL.md` |
| Executing Plans | `skills/collaboration/executing-plans/SKILL.md` |
| Subagent-Driven Development | `skills/collaboration/subagent-driven-development/SKILL.md` |
| Dispatching Parallel Agents | `skills/collaboration/dispatching-parallel-agents/SKILL.md` |
| Using Git Worktrees | `skills/collaboration/using-git-worktrees/SKILL.md` |
| Requesting Code Review | `skills/collaboration/requesting-code-review/SKILL.md` |
| Receiving Code Review | `skills/collaboration/receiving-code-review/SKILL.md` |
| Finishing a Development Branch | `skills/collaboration/finishing-a-development-branch/SKILL.md` |
| Remembering Conversations | `skills/collaboration/remembering-conversations/SKILL.md` |

### testing
| Skill | Path |
|-------|------|
| Test-Driven Development | `skills/testing/test-driven-development/SKILL.md` |
| Condition-Based Waiting | `skills/testing/condition-based-waiting/SKILL.md` |
| Testing Anti-Patterns | `skills/testing/testing-anti-patterns/SKILL.md` |

### debugging
| Skill | Path |
|-------|------|
| Systematic Debugging | `skills/debugging/systematic-debugging/SKILL.md` |
| Root-Cause Tracing | `skills/debugging/root-cause-tracing/SKILL.md` |
| Defense in Depth | `skills/debugging/defense-in-depth/SKILL.md` |
| Verification Before Completion | `skills/debugging/verification-before-completion/SKILL.md` |

### architecture
| Skill | Path |
|-------|------|
| Preserving Productive Tensions | `skills/architecture/preserving-productive-tensions/SKILL.md` |

### problem-solving (techniques for when you're stuck)
| Skill | Path |
|-------|------|
| When Stuck | `skills/problem-solving/when-stuck/SKILL.md` |
| Collision-Zone Thinking | `skills/problem-solving/collision-zone-thinking/SKILL.md` |
| Inversion Exercise | `skills/problem-solving/inversion-exercise/SKILL.md` |
| Meta-Pattern Recognition | `skills/problem-solving/meta-pattern-recognition/SKILL.md` |
| Scale Game | `skills/problem-solving/scale-game/SKILL.md` |
| Simplification Cascades | `skills/problem-solving/simplification-cascades/SKILL.md` |

### research
| Skill | Path |
|-------|------|
| Tracing Knowledge Lineages | `skills/research/tracing-knowledge-lineages/SKILL.md` |

### meta (maintaining the skill library itself)
| Skill | Path |
|-------|------|
| Writing Skills | `skills/meta/writing-skills/SKILL.md` |
| Testing Skills with Subagents | `skills/meta/testing-skills-with-subagents/SKILL.md` |
| Gardening the Skills Wiki | `skills/meta/gardening-skills-wiki/SKILL.md` |
| Sharing Skills | `skills/meta/sharing-skills/SKILL.md` |
| Pulling Updates from the Skills Repository | `skills/meta/pulling-updates-from-skills-repository/SKILL.md` |

## Decision guide (which sub-skill, when)

- Partner describes a rough feature/idea, nothing designed yet → **brainstorming**.
- Design is agreed, need step-by-step tasks for an engineer with zero context → **writing-plans**.
- You have a complete plan and need to implement it safely → **executing-plans** (+ **test-driven-development**).
- Work is large and parallelizable → **subagent-driven-development** / **dispatching-parallel-agents**.
- Need an isolated branch/checkout for the work → **using-git-worktrees**.
- A test fails or behavior is wrong → **systematic-debugging**, then **root-cause-tracing**.
- About to call something "done" → **verification-before-completion**.
- Code is written, ready for review → **requesting-code-review**; got review back → **receiving-code-review**.
- Branch is finished, ready to merge/clean up → **finishing-a-development-branch**.
- Genuinely stuck / spinning → **when-stuck**, then the other **problem-solving** techniques.
- You are editing or adding a skill (including this library) → **meta/writing-skills** and **meta/testing-skills-with-subagents**.

## Notes

- Do not overwrite or edit the sub-skills under `skills/` from here; update them upstream or via
  **meta/pulling-updates-from-skills-repository** and **meta/writing-skills**.
- Many sub-skills are rigid disciplines (TDD, debugging, verification) — follow them exactly,
  don't adapt away the rigor. Some (architecture, problem-solving) are flexible patterns — adapt
  the core principle to context. Each sub-skill states which kind it is.
