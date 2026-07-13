---
name: shadcn-paths-page
description: Migrates PathsPage to shadcn Card, Button, and Badge components. Use proactively during parallel shadcn UI migration — owns PathsPage.tsx only; runs alongside brand and run agents without overlap.
---

You migrate the Paths list page from legacy CSS classes to shadcn/ui components.

## Branch

Work on `cursor/shadcn-paths-7a69` branched from `cursor/shadcn-setup-7a69`.

```bash
cd /workspace
git fetch origin cursor/shadcn-setup-7a69
git checkout -b cursor/shadcn-paths-7a69 origin/cursor/shadcn-setup-7a69
```

## File ownership (exclusive)

| May edit | Must NOT edit |
|----------|---------------|
| `client/src/pages/PathsPage.tsx` only | `Shell.tsx`, `TopNav.tsx`, `RunPage.tsx`, `styles.css`, `App.tsx`, `PageHeader.tsx` |

## Current state

`PathsPage.tsx` uses:
- `className="btn btn-primary"` / `btn-accent` for actions
- `script-grid`, `script-card-*` for path tiles
- `PathBadge` for readiness labels

## Target

- `Button` from `@/components/ui/button` for Create Path and empty-state action
- `Card`, `CardHeader`, `CardContent`, `CardFooter` for path tiles
- shadcn `Badge` from `@/components/ui/badge` for readiness + Example labels:
  - ready → default or success styling via className
  - needs-setup → secondary
  - draft → outline
- Responsive grid via Tailwind (`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4`)
- Keep `StatusBoard`, `EmptyState`, `PageLayout` unchanged
- Preserve all handlers: `openPath`, `handleCreate`, run button navigation

## Constraints

- Use existing shadcn components in `client/src/components/ui/` — do not re-run `shadcn add` unless build fails on missing dep
- Do not delete legacy CSS from styles.css
- Phone/Run button on each card should use `Button` variant outline or secondary with Phone icon

## Workflow

1. Rewrite `PathsPage.tsx` markup only
2. Run `cd /workspace/client && npm run build`
3. Commit: `Migrate PathsPage to shadcn Card, Button, Badge`
4. Push: `git push -u origin cursor/shadcn-paths-7a69`
