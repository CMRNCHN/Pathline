---
name: ui-integration-merge
description: Merges parallel shadcn UI branches (brand, paths, run, shell) into a single integration branch with green build and PR. Use proactively after wave 1 and wave 2 branches are pushed — wave 3 of shadcn migration.
---

You integrate parallel shadcn UI migration branches into one mergeable PR.

## When invoked

All four feature branches must exist on origin:
- `cursor/shadcn-brand-7a69`
- `cursor/shadcn-paths-7a69`
- `cursor/shadcn-run-ui-7a69`
- `cursor/shadcn-shell-7a69`

## Workflow

```bash
cd /workspace
git fetch origin
git checkout -b cursor/shadcn-ui-integration-7a69 origin/cursor/shadcn-setup-7a69
```

Merge in order (lowest conflict risk first):

```bash
git merge origin/cursor/shadcn-brand-7a69 -m "Merge shadcn brand tokens"
git merge origin/cursor/shadcn-paths-7a69 -m "Merge shadcn Paths page"
git merge origin/cursor/shadcn-run-ui-7a69 -m "Merge shadcn Run UI"
git merge origin/cursor/shadcn-shell-7a69 -m "Merge shadcn Sidebar shell"
```

## Conflict resolution

| File | Rule |
|------|------|
| `client/src/styles.css` | Keep brand token changes from brand branch; preserve any shell/page unrelated edits |
| `client/src/App.tsx` | Prefer shell branch layout changes; keep view state from base |
| `client/src/pages/PathsPage.tsx` | Prefer paths branch |
| `client/src/pages/RunPage.tsx` | Prefer run branch |
| `client/src/components/Shell.tsx` | Prefer shell branch |

Do not add feature work — only resolve merge conflicts.

## Verification

```bash
cd /workspace/client && npm run build
```

## Ship

```bash
git push -u origin cursor/shadcn-ui-integration-7a69
```

Open or update PR:
- **Title:** shadcn UI migration — Sidebar, Paths, Run, brand tokens
- **Base:** `cursor/known-scripts-and-run-automation`
- **Body:** List merged branches, test plan (build + manual Paths/Run/Settings smoke)

Optionally merge PR #12 first if integration branch should target an already-merged base.

## Final summary

Report:
- Branches merged
- Conflicts resolved (files touched)
- Build status
- PR URL
