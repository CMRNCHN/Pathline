---
name: merge-callstate-rename
description: Resolves merge conflicts for PR #7 (cursor/callstate-rename-7a69) against cursor/known-scripts-and-run-automation. Use proactively when callstate/LiveStatus projection work conflicts with Pathline vocabulary changes (Status, Run, Path terms).
---

You resolve merge conflicts for the **callstate rename** branch into the current base.

## Branch & PR

- **Branch:** `cursor/callstate-rename-7a69`
- **PR:** #7 — Event-sourced callstate projections (rename from status)
- **Base:** `cursor/known-scripts-and-run-automation` (includes Pathline vocabulary from PR #9)

## What this branch introduces

- New module: `client/src/callstate/` — `CallEvent`, `Path`, `CallState` types
- `projectCallState()` — deterministic projection from event ledger
- `formatCallStateText()` — active/completed text output
- Renames runtime **status** model to **callstate** / **LiveStatus** projection

## Likely conflict areas

- `RunPage.tsx` — both branches touch Run/Status UI and terminology
- `client/src/types.ts` or session types — status vs callstate naming
- Any file referencing `session.status`, `LocalSession`, or status badges
- Pathline renamed "Status" as the Run execution view; callstate branch may still use old terms

## Workflow

1. `git fetch origin cursor/known-scripts-and-run-automation cursor/callstate-rename-7a69`
2. `git checkout cursor/callstate-rename-7a69`
3. `git merge origin/cursor/known-scripts-and-run-automation` (or rebase if preferred)
4. Classify each conflict:
   - **Simple:** rename-only (`status`→Pathline Status, `script`→Path, field renames)
   - **Complicated:** both branches changed the same behavior (projection logic vs UI consolidation)
5. Resolve simple conflicts; report complicated ones with file + rationale
6. Prefer **Pathline front-facing terms** (Path, Step, Run, Status, History) while keeping callstate projection internals
7. Run `cd client && npm run build`
8. Commit, push `-u origin cursor/callstate-rename-7a69`, update PR #7

## Resolution principles

- Pathline vocabulary wins for **user-facing** labels
- Callstate projection model wins for **internal** event-sourced architecture
- Do not revert PR #9 screen consolidation (Paths, History, merged Settings)
- Keep `LiveStatus` as a read-only projection, not a competing navigation concept

## Output format

Report:
1. Conflicts fixed (file list)
2. Conflicts needing human decision (file, both intents, recommendation)
3. Build result
4. Push status
