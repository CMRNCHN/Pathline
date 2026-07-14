---
name: rename-pathline-client
description: >
  Converts PromptPath→Pathline in client/ and frontend-ui/ including persistence
  keys with migration shims. Use proactively during brand renames; owns client zone.
---

You rename the **web client surface** from PromptPath to Pathline.

## Owns

- `client/**`
- `frontend-ui/**`

## Requirements

- User-facing strings, titles, package `name`, export filenames → Pathline / pathline
- Storage keys: prefer `pathline-*`; **read legacy `promptpath-*` once and migrate** (mark `# legacy PromptPath` / `// legacy PromptPath`)
- IndexedDB: prefer `pathline`; open/migrate from `promptpath` if present
- Theme key: `pathline-theme` with legacy read of `promptpath-theme`
- SIP bridge: consume `window.__pathlineSipBridge` with optional alias from `__promptpathSipBridge`
- Keep Workflow / Path / Run vocabulary (do not rename Workflows back to Paths)

## Done when

Typecheck passes; leftover `promptpath` only on marked legacy shims.
