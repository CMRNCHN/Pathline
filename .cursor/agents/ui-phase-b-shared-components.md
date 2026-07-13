---
name: ui-phase-b-shared-components
description: Migrates shared UI primitives to shadcn — PageLayout, EmptyState, RunStepBar, StatusBoard. Use proactively in wave 1 parallel with phases C and D; exclusive file ownership.
---

You execute Phase B — shared components used across all pages.

## Branch

`cursor/ui-shared-components-7a69` from `origin/cursor/known-scripts-and-run-automation` (after Phase A).

## Exclusive ownership

| Edit | Do NOT edit |
|------|-------------|
| `client/src/components/ui/PageHeader.tsx` | Pages, Shell, styles.css |
| `client/src/components/ui/EmptyState.tsx` | |
| `client/src/components/ui/RunStepBar.tsx` | |
| `client/src/components/StatusBoard.tsx` | |

## Targets

- **PageLayout**: Tailwind + shadcn typography; keep same props API
- **EmptyState**: Card or centered flex with muted text; accept `action` ReactNode (already shadcn Button from parents)
- **RunStepBar**: horizontal step indicator with shadcn Badge/Button styling or custom Tailwind (no legacy `.run-step-*` classes)
- **StatusBoard**: grid of shadcn `Card` tiles; keep `buildTiles` logic and refresh button; use Badge for state dots

## Verify

```bash
cd /workspace/client && npm run build
git push -u origin cursor/ui-shared-components-7a69
```
