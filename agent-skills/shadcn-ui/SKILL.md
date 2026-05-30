---
name: shadcn-ui
description: Use when building or modifying UI in a project that uses (or should use) shadcn/ui — adding components like button/dialog/form/table, theming via CSS variables, dark mode, Tailwind setup, or installing from registries. Trigger when the repo has a components.json, when imports come from "@/components/ui/*", when the user mentions "shadcn", "shadcn/ui", "radix-based components", or asks to add/scaffold UI primitives. Always read components.json first and respect its style/baseColor/aliases.
---

# shadcn/ui — project-aware UI workflow

shadcn/ui is **not a component library you install as a dependency**. The CLI **copies
component source code into your project** (default `@/components/ui/*`). You own the files
and edit them freely. There is no `import { Button } from "shadcn"` — you import from your
own path alias (e.g. `import { Button } from "@/components/ui/button"`).

Canonical sources (verified):
- Skills: https://ui.shadcn.com/docs/skills
- CLI: https://ui.shadcn.com/docs/cli
- components.json: https://ui.shadcn.com/docs/components-json
- MCP: https://ui.shadcn.com/docs/mcp

Commands below use `npx shadcn@latest …`. The official docs use `pnpm dlx shadcn@latest …`;
both are equivalent — match the project's package manager (`npx` for npm, `pnpm dlx` for pnpm,
`yarn dlx` / `bunx --bun shadcn@latest` accordingly). The package is `shadcn` (the old
`shadcn-ui` package name is deprecated — do not use it).

---

## Step 0 — Detect project state BEFORE touching anything

Run this decision first, every time:

1. **Look for `components.json`** at the project root (use Glob/Read, do not assume).
2. If it exists → **READ IT and respect every field** (see "Reading components.json" below).
   Do NOT run `init` again — it would overwrite config.
3. If it is absent → the project is not initialized. Guide/run `init` (see "Initializing").
4. If a richer signal is available, prefer the CLI's own introspection:
   ```bash
   npx shadcn@latest info --json
   ```
   This returns the resolved project config: framework, Tailwind version, path aliases,
   base library (`radix` or `base`), icon library, and **installed components**. Use it to
   avoid re-adding components that already exist and to learn the real aliases.

Never hardcode paths like `src/components/ui` — always derive them from `components.json`
aliases or `info --json`.

---

## Reading components.json (the contract you must respect)

Every key and how it changes what you generate:

| Key | Meaning | Why it matters for you |
|-----|---------|------------------------|
| `$schema` | `https://ui.shadcn.com/schema.json` | Validation only. |
| `style` | `"new-york"` (the old `"default"` is deprecated) | Determines variant markup the CLI emits. Keep consistent. |
| `rsc` | `true` \| `false` — React Server Components support | If `true`, generated client components get `"use client"`. Match it in code you write by hand. |
| `tsx` | `true` \| `false` | `true` → `.tsx`/`.ts`; `false` → `.jsx`/`.js`. Write files in the matching language. |
| `tailwind.config` | path to `tailwind.config.{js,ts}` | **Empty string for Tailwind v4** (config moved into CSS). Non-empty → Tailwind v3. This tells you which Tailwind major you're on. |
| `tailwind.css` | path to the CSS entry that imports Tailwind | Where theme tokens / `@theme` / `:root` variables live. Edit theming here. |
| `tailwind.baseColor` | `neutral` \| `stone` \| `zinc` \| `gray` \| `slate` (plus newer: `mauve`, `olive`, `mist`, `taupe`) | Base palette. Cannot be changed retroactively via config alone — it seeds the CSS variables. |
| `tailwind.cssVariables` | `true` \| `false` | `true` → theme via CSS variables (`bg-background`, `text-foreground`). `false` → utility classes are written with literal colors. Generate components accordingly. |
| `tailwind.prefix` | e.g. `"tw-"` | If set, ALL Tailwind classes you write must carry this prefix. |
| `aliases.components` | e.g. `@/components` | Base for non-ui components. |
| `aliases.ui` | e.g. `@/components/ui` | **Where primitives land.** Import from here. |
| `aliases.lib` | e.g. `@/lib` | Library/helpers. |
| `aliases.utils` | e.g. `@/lib/utils` | Location of `cn()` helper — import `cn` from here. |
| `aliases.hooks` | e.g. `@/hooks` | Generated hooks (e.g. `use-mobile`). |
| `iconLibrary` | `lucide` \| `radix` (icon set used by components) | Use this icon set in code you add so it matches. |
| `registries` | named registry URL templates + optional auth headers | Lets `add`/`search`/`view` pull from custom/private registries via namespaces like `@acme/button`. |

Practical rule: after reading `components.json`, mirror its decisions in any hand-written
component — same path aliases, same `cn()` import, same `"use client"` policy, same Tailwind
version idioms, same icon library, same prefix.

---

## Initializing (only when components.json is ABSENT)

```bash
npx shadcn@latest init
```

Interactive prompts cover style, base color, and CSS-variables choice; it writes
`components.json`, sets up `tailwind` + global CSS tokens, adds the `cn()` util, and installs
peer deps (Radix primitives, `clsx`, `tailwind-merge`, `class-variance-authority`, icon lib).

Useful `init` flags (verified): `--template`, `--base` (`radix` | `base`), `--preset`,
`--css-variables`, `--monorepo`, `--rtl`.

Prereqs to confirm first: a framework (Next.js, Vite+React, Remix, Astro, Laravel, etc.),
Tailwind installed, and TS path aliases configured in `tsconfig.json`/`jsconfig.json`
(e.g. `"@/*": ["./src/*"]`) so the `@/` aliases resolve.

---

## Adding components

```bash
npx shadcn@latest add button
npx shadcn@latest add button dialog card        # multiple at once
npx shadcn@latest add                            # interactive multiselect
```

Verified flags: `--all`, `--overwrite`, `--dry-run`, `--path <dir>`.

- `--dry-run` first when unsure what files would be touched.
- `--overwrite` only when you intend to reset a customized file to upstream.
- From a custom/private registry use the namespace: `npx shadcn@latest add @acme/login-form`.
- After adding, components live in `aliases.ui`. **Edit them in place** — they are your code,
  not node_modules. To pull upstream improvements later, re-add with `--overwrite` (you lose
  local edits) or diff manually.

Inspect before installing:
```bash
npx shadcn@latest view button            # show item source/metadata from registry
npx shadcn@latest search @shadcn --query table   # search a registry
```
Verified `search` flags: `--query`, `--limit`, `--offset`.

Other verified commands: `diff` (compare local vs registry), `info` (project diagnostics),
`build` (`--output`; generate registry JSON when authoring your own registry).

---

## Theming — CSS variables, OKLCH, dark mode

If `tailwind.cssVariables` is `true` (the common case), theming is done by editing CSS
variables in the file at `tailwind.css`, NOT by hardcoding hex in components.

- Tokens are semantic: `--background`, `--foreground`, `--primary`, `--primary-foreground`,
  `--muted`, `--accent`, `--destructive`, `--border`, `--input`, `--ring`, `--radius`, etc.
  Components reference them via Tailwind classes like `bg-background`, `text-foreground`,
  `border-border`, `bg-primary text-primary-foreground`.
- Modern shadcn uses **OKLCH** color values for tokens (wide gamut, perceptually uniform).
- **Dark mode** is class-based: a `.dark { … }` block redefines the same variables. Toggle by
  adding/removing the `dark` class on `<html>` (commonly via `next-themes` in Next.js, or a
  manual class toggle). Do not duplicate component code for dark mode — only the CSS vars
  differ.
- Change radius globally via `--radius`. Change a brand color by editing `--primary` (+ its
  `-foreground` pair) in both `:root` and `.dark`.
- Tailwind v4: tokens are exposed through `@theme` / `@theme inline` in the CSS file (no JS
  config). Tailwind v3: extend `theme.extend.colors` in `tailwind.config` mapping to the
  `hsl(var(--token))` / `var(--token)` variables. Detect the version via whether
  `tailwind.config` is empty.

Apply preset themes/fonts (verified): `npx shadcn@latest apply <preset> --only theme|font`.

---

## MCP server (registry discovery & install via natural language)

The shadcn MCP server lets an agent browse, search, and install registry items
conversationally. Set up for Claude Code (verified):

```bash
npx shadcn@latest mcp init --client claude
```

Or add manually to `.mcp.json`:
```json
{
  "mcpServers": {
    "shadcn": { "command": "npx", "args": ["shadcn@latest", "mcp"] }
  }
}
```
(Cursor uses `.cursor/mcp.json`, VS Code `.vscode/mcp.json`, same structure.)

It exposes: browse/list items, search across registries, install with natural language, and
multi-registry support (public, private, third-party). Example prompts: "Show me all available
components in the shadcn registry", "Add the button, dialog and card components to my project".
Prefer the MCP when configured; otherwise drive the CLI directly.

---

## Common components → canonical add commands

```bash
npx shadcn@latest add button
npx shadcn@latest add input label textarea
npx shadcn@latest add form            # react-hook-form + zod wiring
npx shadcn@latest add dialog
npx shadcn@latest add alert-dialog
npx shadcn@latest add dropdown-menu
npx shadcn@latest add select
npx shadcn@latest add popover
npx shadcn@latest add tooltip
npx shadcn@latest add card
npx shadcn@latest add badge
npx shadcn@latest add avatar
npx shadcn@latest add tabs
npx shadcn@latest add accordion
npx shadcn@latest add table
npx shadcn@latest add sheet
npx shadcn@latest add toast           # or: add sonner  (toasts are migrating to sonner)
npx shadcn@latest add sonner
npx shadcn@latest add command         # command palette / combobox base
npx shadcn@latest add calendar
npx shadcn@latest add checkbox switch radio-group
npx shadcn@latest add skeleton
npx shadcn@latest add navigation-menu
npx shadcn@latest add sidebar
npx shadcn@latest add pagination
npx shadcn@latest add separator scroll-area
```

Notes: a **combobox** is composed from `command` + `popover` (no single `combobox` add). A
**data table** is built on `table` + TanStack Table (follow the docs recipe). If `add` reports
an unknown item, run `search` to find the correct registry name rather than guessing.

---

## Verification checklist before declaring done

- [ ] Read `components.json` (or ran `info --json`) and respected `style`, `baseColor`,
      `cssVariables`, `tsx`, `rsc`, `prefix`, `iconLibrary`, and all `aliases`.
- [ ] New components imported from `aliases.ui`; `cn` imported from `aliases.utils`.
- [ ] No hardcoded colors when `cssVariables: true` — used semantic Tailwind tokens.
- [ ] `"use client"` present on interactive components when `rsc: true`.
- [ ] Tailwind class prefix applied if `prefix` is set.
- [ ] Did not re-run `init` on an already-initialized project; did not blow away customized
      files with `--overwrite` unintentionally.
- [ ] Dark mode works via the `.dark` variable block, not duplicated markup.
- [ ] Used the correct package manager invocation (`npx`/`pnpm dlx`/`yarn dlx`/`bunx`).

## Anti-patterns

- Treating shadcn as an npm component dependency / importing from a package named `shadcn`.
- Using the deprecated `shadcn-ui` CLI package or `style: "default"`.
- Hardcoding hex colors instead of editing CSS variables.
- Re-running `init` and clobbering an existing `components.json`.
- Guessing component names — verify with `search`/`view` or the docs registry.
