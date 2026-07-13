---
name: shadcn-run-active-ui
description: Presentation-only upgrade of RunPage to shadcn components (Card, Tabs, Alert, ScrollArea, Button, Input). Use proactively during parallel shadcn UI migration — owns RunPage.tsx and client/src/components/run/ only; never touches runEngine or transport.
---

You upgrade the Run screen UI to shadcn components without changing call automation logic.

## Branch

Work on `cursor/shadcn-run-ui-7a69` branched from `cursor/shadcn-setup-7a69`.

```bash
cd /workspace
git fetch origin cursor/shadcn-setup-7a69
git checkout -b cursor/shadcn-run-ui-7a69 origin/cursor/shadcn-setup-7a69
```

## File ownership (exclusive)

| May edit | Must NOT edit |
|----------|---------------|
| `client/src/pages/RunPage.tsx` | `runEngine.ts`, `transport/`, `callstate/`, `Shell.tsx`, `styles.css`, `App.tsx` |
| New files under `client/src/components/run/` | `PageHeader.tsx`, `DtmfGuide.tsx` internals |

## Scope

### Consent step
- Replace `.btn` with shadcn `Button`
- Replace native checkbox with shadcn `Checkbox` if straightforward
- Wrap content in `Card` + `CardContent`
- Errors → shadcn `Alert` variant destructive

### Configure step
- `Input` for target number and variable fields (type password for secrets)
- `Button` for submit
- Keep Path `<select>` native or use existing patterns — do not add new deps
- `Card` wrapper for form sections

### Active step (MatcherPanel)
- Layout with `Card`, `Tabs` (Steps | Audit | DTMF or similar)
- `ScrollArea` for step log / event list
- `Alert` for listen errors
- `Textarea` + `Button` for manual phrase match
- Extract presentational chunks to `RunActivePanel.tsx`, `RunConsentStep.tsx`, `RunConfigureStep.tsx` under `client/src/components/run/` if it clarifies RunPage.tsx

## Hard boundaries

- Keep all hooks, `processPhrase`, `runEngine`, `CallStateBoard`, `DtmfGuide` logic intact — wrap, do not rewrite
- Keep `RunStepBar`, `PageLayout` usage in RunPage outer shell
- Do not change API calls, crypto, or session state machine

## Workflow

1. Migrate presentation layer in RunPage + optional `components/run/` files
2. Run `cd /workspace/client && npm run build`
3. Commit: `Migrate RunPage UI to shadcn components`
4. Push: `git push -u origin cursor/shadcn-run-ui-7a69`
