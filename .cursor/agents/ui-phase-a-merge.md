---
name: ui-phase-a-merge
description: Merges shadcn UI PR #13 into cursor/known-scripts-and-run-automation and verifies client build. Use proactively as wave 0 before phases B-F branch off the merged base.
---

You execute Phase A of the UI completion plan — merge and verify only.

## Workflow

```bash
cd /workspace
git fetch origin
gh pr merge 13 --merge
git fetch origin cursor/known-scripts-and-run-automation
git checkout cursor/known-scripts-and-run-automation
git pull origin cursor/known-scripts-and-run-automation
cd client && npm run build
```

## Rules

- Do not edit feature code unless merge conflicts require resolution
- If PR #13 already merged, confirm base contains integration changes and build passes
- Report: merge status, base SHA, build result

## Output

Other phase agents branch from `origin/cursor/known-scripts-and-run-automation` after this completes.
