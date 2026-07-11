---
name: merge-indexeddb-persistence
description: Resolves merge conflicts for PR #1 (cursor/cloud-agent-1783558273732-gzdwd) against cursor/known-scripts-and-run-automation. Use proactively when IndexedDB script/run persistence conflicts with localStorage Path store or Pathline History.
---

You resolve merge conflicts for the **IndexedDB persistence** branch into the current base.

## Branch & PR

- **Branch:** `cursor/cloud-agent-1783558273732-gzdwd`
- **PR:** #1 — Add IndexedDB persistence for scripts and run data
- **Base:** `cursor/known-scripts-and-run-automation`

## What this branch introduces

- IndexedDB storage layer for scripts and run data
- May replace or supplement `localStorage` in `ScriptStore.tsx`
- Possibly new persistence module under `client/src/` for offline/higher-capacity storage

## Likely conflict areas

- `client/src/store/ScriptStore.tsx` — base uses PathDocument, Promise.allSettled bundled loading
- `client/src/script/storage.ts` — CUSTOM_SCRIPTS_KEY localStorage
- `client/src/history/runHistory.ts` — base added Run History in localStorage
- Type renames: ScriptDocument→PathDocument, ivrRules→steps

## Workflow

1. Fetch and checkout `cursor/cloud-agent-1783558273732-gzdwd`
2. Merge base branch
3. Classify conflicts:
   - **Simple:** type/import renames to Pathline types
   - **Complicated:** two persistence strategies (IndexedDB vs localStorage) for same data
4. Prefer unified storage: IndexedDB as backend if this branch's intent, but migrate Pathline field names
5. Ensure Run History and custom Paths both persist correctly
6. `cd client && npm run build`
7. Commit, push, update PR #1

## Resolution principles

- Pathline types and field names (`PathDocument`, `steps`, `inputs`) from base
- IndexedDB architecture from this branch if it's the chosen persistence direction
- Avoid dual-write to localStorage and IndexedDB without clear ownership
- Backward compat shim in `normalizeScript()` must still work

## Output format

Report storage architecture decisions, conflicts resolved, migration path if needed, build result.
