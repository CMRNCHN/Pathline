---
name: merge-scripts-status-board
description: Resolves merge conflicts for PR #5 (cursor/scripts-status-board-7a69) against cursor/known-scripts-and-run-automation. Use proactively when the Scripts dashboard status board conflicts with Pathline Paths page redesign.
---

You resolve merge conflicts for the **scripts status board** branch into the current base.

## Branch & PR

- **Branch:** `cursor/scripts-status-board-7a69`
- **PR:** #5 — Condensed animated status board on Scripts page
- **Base:** `cursor/known-scripts-and-run-automation` (Paths page replaced LibraryPage)

## What this branch introduces

- Animated condensed status board on the scripts dashboard
- Script readiness badges (ready / draft / needs-setup)
- Card-based script list enhancements
- References `LibraryPage.tsx`, "Scripts" navigation, script-card CSS

## Likely conflict areas

- `LibraryPage.tsx` — **deleted** on base, replaced by `PathsPage.tsx`
- `client/src/pages/PathsPage.tsx` — base has Pathline card list; this branch adds status board
- `client/src/script/pathReadiness.ts` or `scriptStatus.ts` — may overlap with base
- `client/src/styles.css` — script-card / path-card / badge styles
- `TopNav.tsx`, `navigation.ts` — "Scripts" vs "Paths"

## Workflow

1. Fetch and checkout `cursor/scripts-status-board-7a69`
2. Merge `origin/cursor/known-scripts-and-run-automation`
3. **Port** status board UI from old LibraryPage into `PathsPage.tsx` (do not restore LibraryPage)
4. Rename terminology: Scripts→Paths, script→Path where user-facing
5. Reuse `getPathReadiness` / readiness badges from base if present; merge animation from branch
6. `cd client && npm run build`
7. Commit, push, update PR #5

## Complicated vs simple

- **Simple:** CSS class renames, badge variant names, import path updates
- **Complicated:** Entire page structure moved — status board must be reimplemented on PathsPage, not LibraryPage

## Resolution principles

- Base architecture wins: PathsPage is the home screen
- Status board animation/readiness from this branch should survive the port
- One card-based list with readiness badges — no duplicate dashboards

## Output format

Report what was ported to PathsPage, conflicts resolved, build result, push status.
