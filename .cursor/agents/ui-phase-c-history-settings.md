---
name: ui-phase-c-history-settings
description: Migrates HistoryPage and SettingsPage to shadcn Card, Table, Button, Badge. Use proactively in wave 1 parallel with phases B and D.
---

You execute Phase C — History and Settings pages.

## Branch

`cursor/ui-history-settings-7a69` from `origin/cursor/known-scripts-and-run-automation`.

## Exclusive ownership

| Edit | Do NOT edit |
|------|-------------|
| `client/src/pages/HistoryPage.tsx` | Edit pages, shared components, styles.css, Shell |
| `client/src/pages/SettingsPage.tsx` | |

## Targets

- Replace `PathBadge` with shadcn `Badge` (map outcome variants)
- Replace `.history-*` layout with Card + ScrollArea or Table from `@/components/ui/table`
- Replace `SectionCard` usage with shadcn `Card`, `CardHeader`, `CardTitle`, `CardContent`
- Replace all `.btn` with shadcn `Button`
- Keep all data logic (loadRunHistory, export, delete) unchanged

## Verify

```bash
cd /workspace/client && npm run build
git push -u origin cursor/ui-history-settings-7a69
```
