---
name: ui-phases-integration
description: Merges wave 1 branches (B,C,D), then E, then F into cursor/ui-complete-7a69 with green build and PR. Use proactively after parallel phase branches are pushed.
---

You integrate Phases A–F into one shippable PR.

## Merge order

```bash
cd /workspace
git fetch origin
git checkout -b cursor/ui-complete-7a69 origin/cursor/known-scripts-and-run-automation

# Wave 1 (parallel branches — merge in any order, resolve conflicts by ownership)
git merge origin/cursor/ui-shared-components-7a69 -m "Merge phase B shared components"
git merge origin/cursor/ui-history-settings-7a69 -m "Merge phase C history settings"
git merge origin/cursor/ui-edit-wizard-7a69 -m "Merge phase D edit wizard"

# Wave 2
git merge origin/cursor/ui-brand-cleanup-7a69 -m "Merge phase E brand cleanup"

# Wave 3
git merge origin/cursor/ui-polish-7a69 -m "Merge phase F polish"

cd client && npm run build
git push -u origin cursor/ui-complete-7a69
```

## Conflict rules

- PageHeader/StatusBoard → B wins
- HistoryPage/SettingsPage → C wins
- EditForm/wizard/DtmfGuide → D wins
- styles.css → E wins
- ThemeToggle/RunConfigureStep select → F wins

Open PR to `cursor/known-scripts-and-run-automation` titled "Complete shadcn UI migration (phases A–F)".
