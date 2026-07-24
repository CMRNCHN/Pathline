---
name: pathline-figma-mcp
description: >
  Pathline Figma MCP workflow using real Cursor Figma skills, paste-ready
  phase prompts, and Figma free/Starter limitations. Use when designing
  Pathline Desktop in Figma or when the orchestrator assigns Figma work.
disable-model-invocation: true
---

# Pathline Figma MCP

## Real skills (not aliases)

| Phase | Load these |
|-------|------------|
| New file | `figma-create-new-file` then `figma-use` |
| Tokens / components | `figma-generate-library` + `figma-use` |
| Screens | `figma-generate-design` + `figma-use` |
| IA flowchart | `figma-generate-diagram` (+ `figma-use-figjam` if FigJam) |
| Later code from Figma | `figma-design-to-code` (implementer, not figma agent) |

Always load **`figma-use` before every `use_figma`**.

## Figma free / Starter — how it changes the plan

Assume **Figma Starter (free)** unless the user says otherwise.

| Feature | Free impact | Pathline adaptation |
|---------|-------------|---------------------|
| File count | Tight budget on shared/team files | **One** file: `Pathline Desktop`; use **pages**, not many files |
| Team libraries | Publishing shared libraries is paid | Keep components **local to the file**; no “publish library” step |
| Variables / modes | Basic variables OK; advanced modes limited | Light + dark only if it works; else single theme + note |
| Dev Mode | Full inspect/redlines often paid | Handoff via MCP `get_screenshot` / `get_design_context` + annotated frames — **not** Dev Mode |
| Code Connect | Typically paid / org | **Skip Code Connect on free**; map components in a markdown handoff note instead |
| Prototyping | Simple click-through OK; advanced may be limited | Sidebar + list→detail→Edit/Dial links only |
| FigJam | Limited free files | Prefer a **Flows page inside the design file**; one FigJam only if needed |
| History | Short version history | Bigger milestones = export PDF/PNG checklist in repo if needed |
| Seats / collab | Limited editors | One agent + one human editor at a time |

**Do not** block the product on paid Figma features. Design for handoff that works with MCP + existing `client/src/components/ui`.

### Budget check (orchestrator must pass before a Figma wave)

```
[ ] Using existing Pathline Desktop file OR this is the single allowed create_new_file
[ ] No second Figma/FigJam file
[ ] No Code Connect / Dev Mode / publish library
[ ] One editor (agent or human), not both
[ ] Wave adds pages/frames in-file only
```

If any box fails → **do not run** the Figma wave; do a **code UX wave** instead or wait.

**Maximize free-plan value:** one file, local components, Shell + Path Library first, simple prototypes, MCP screenshots for handoff — skip paid-only features rather than upgrading mid-project.

## Locked product constraints (every prompt)

- Desktop ~1280×800
- Five surfaces only: Dashboard, Path Library, Accounts, Input Vault, System
- List+detail; Edit|Dial tabs inside Path detail
- Secrets never in Path JSON
- Mirror shadcn/Radix/Tailwind — no MUI/Chakra look
- Defer: detachable Run window, three-column Path detail

## Phase prompts (paste)

### 1 — File + pages

```
Create a new Figma design file named "Pathline Desktop".
Add pages: Foundations, Shell, Dashboard, Path Library, Accounts,
Input Vault, System, Flows. Do not create extra files.
No Templates/Runs/Settings/Edit top-level app pages.
```

### 2 — Foundations

```
On Foundations, add variables mirroring client/src/styles.css and
primitives: Button, Input, Badge, Card, Tabs, Table, Dialog/Select,
Sidebar. Local components only (no published team library). Auto-layout.
```

### 3 — Shell

```
Shell page: ~1280×800 chrome, 240px sidebar with five items only,
breadcrumb + content outlet. Five artboards sharing the shell.
```

### 4 — Path Library

```
List+detail: left search/New/readiness/last-run; right header + Edit|Dial tabs.
```

### 5 — Accounts + Vault

```
Accounts list+detail with plain/secret fields + vault selector (search, New secret).
Input Vault list + add secret. Suggest-fields-from-Path preview. No raw secrets in Path JSON mocks.
```

### 6 — Dashboard + System

```
Dashboard: status, quick actions, recent activity.
System: health, local data, crypto. No Settings page.
```

### 7 — Flows

```
Prototype: sidebar routes; Path row→detail→Edit→Dial; Account secret→Vault dialog.
Flows page: readiness diagram. Skip detach Run / 3-column detail.
```

### 8 — Handoff (free)

```
Do not set up Code Connect. Instead: annotate key frames with component names
matching client/src/components/ui/*, export a short page checklist + file URL
for the orchestrator. Implementers will use get_design_context when coding.
```

## Agent

Figma writes: **`pathline-figma-design`** only. Orchestrator: **`pathline-orchestrator`**.
