---
name: ui-phase-d-edit-wizard
description: Migrates Edit page, RuleCard, EditForm, rule wizard steps, and DtmfGuide to shadcn Button/Card/Input. Use proactively in wave 1 parallel with phases B and C — largest UI surface.
---

You execute Phase D — Edit path and rule wizard.

## Branch

`cursor/ui-edit-wizard-7a69` from `origin/cursor/known-scripts-and-run-automation`.

## Exclusive ownership

| Edit | Do NOT edit |
|------|-------------|
| `client/src/pages/edit/EditForm.tsx` | History, Settings, PageHeader, StatusBoard, styles.css |
| `client/src/pages/edit/RuleCard.tsx` | |
| `client/src/pages/edit/ruleWizard/**/*.tsx` | RunPage, Shell |
| `client/src/components/DtmfGuide.tsx` | |

## Targets

- All `.btn` → shadcn `Button` (preserve sizes via `size="sm"` etc.)
- `PathBadge` → shadcn `Badge`
- Editor sections → `Card` where it clarifies layout
- Wizard steps: `Input`, `Textarea`, `Button` from shadcn
- DtmfGuide: Button variants only; keep timer/sequence logic

## Verify

```bash
cd /workspace/client && npm run build
git push -u origin cursor/ui-edit-wizard-7a69
```
