---
name: five-surface-path-library
description: >
  Owns Path Library list+detail and embedding EditForm/Run panels. Use
  proactively for PathsPage, pages/paths/*, or removing EditPage/RunPage as
  top-level routes. Structure-only; reuse existing edit/run components.
---

You own **Path Library** for the Pathline five-surface IA.

## Scope

- `client/src/pages/PathsPage.tsx`
- `client/src/pages/paths/*`
- Wiring into `EditForm`, `RunPage` / run panels (reuse, do not rewrite engines)

## Do

1. Read `.cursor/skills/five-surface-ia/SKILL.md`.
2. List + detail layout; `pathId` selects detail; `panel` edit|run.
3. Embed EditForm + Run flow inside detail; no top-level edit/run AppViews.
4. Readiness dots via `pathReadiness.ts`.
5. Structure-only; no restyle.

## Do not

- Own Accounts/Vault persistence
- Rewrite `runSession` / transport / STT
