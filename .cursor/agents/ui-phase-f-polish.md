---
name: ui-phase-f-polish
description: Adds dark mode toggle, shadcn Select on Run configure, and mobile sidebar polish. Use proactively in wave 3 after Phase E.
---

You execute Phase F — polish and UX.

## Branch

`cursor/ui-polish-7a69` from Phase E branch.

## Exclusive ownership

| Edit | Do NOT edit |
|------|-------------|
| New `client/src/components/ThemeToggle.tsx` | styles.css token definitions (E owns) |
| `client/src/main.tsx` — only if needed for theme class | Page content beyond Run configure |
| `client/src/components/Shell.tsx` — header slot for ThemeToggle | |
| `client/src/components/AppSidebar.tsx` — mobile spacing only | |
| `client/src/components/run/RunConfigureStep.tsx` — native select → shadcn Select | |

## Targets

- **Dark mode**: toggle adds/removes `dark` class on `document.documentElement`; use existing `.dark` tokens in styles.css
- **Select**: `npx shadcn@latest add select -y` if missing; wire Path picker in RunConfigureStep
- **Mobile**: verify Sidebar sheet on narrow viewport; add `min-w-0` / padding fixes if needed

## Verify

```bash
cd /workspace/client && npm run build
git push -u origin cursor/ui-polish-7a69
```
