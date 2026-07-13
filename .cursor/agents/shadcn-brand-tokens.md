---
name: shadcn-brand-tokens
description: Maps shadcn/Nova CSS variables to PromptPath brand tokens in styles.css only. Use proactively when migrating UI to shadcn — runs in parallel with page agents; must not touch any .tsx files.
---

You migrate Nova/shadcn CSS variables to the PromptPath brand without touching React components.

## Branch

Work on `cursor/shadcn-brand-7a69` branched from `cursor/shadcn-setup-7a69`.

```bash
cd /workspace
git fetch origin cursor/shadcn-setup-7a69
git checkout -b cursor/shadcn-brand-7a69 origin/cursor/shadcn-setup-7a69
```

## File ownership (exclusive)

| May edit | Must NOT edit |
|----------|---------------|
| `client/src/styles.css` — only `:root` shadcn token block (~lines 51–77), `.dark` mirror (~2620+), and `@theme` font tokens (~lines 8–16) | Any `.tsx` file; legacy `.script-card`, `.topnav`, `.btn` CSS blocks |

## Token targets

- `--primary` → brand purple `#5c5c9a` (oklch equivalent acceptable)
- `--primary-foreground` → readable on primary (white or near-white)
- `--radius` → `0.75rem` (12px)
- `--font-sans` / body → DM Sans (already in `@theme`; wire shadcn body to use it)
- `--font-mono` → IBM Plex Mono
- `--sidebar-primary` → align with brand purple `#5c5c9a`
- `--sidebar-primary-foreground` → readable contrast

Do not remove legacy CSS variables used by unmigrated pages.

## Workflow

1. Edit only the shadcn token sections listed above in `client/src/styles.css`
2. Run `cd /workspace/client && npm run build`
3. Commit: `Map shadcn tokens to PromptPath brand`
4. Push: `git push -u origin cursor/shadcn-brand-7a69`

## Verification

- Build passes
- No `.tsx` files changed
- Legacy pages still render (vars preserved)
