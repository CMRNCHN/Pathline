---
name: ui-phase-e-brand-cleanup
description: Unifies PromptPath branding, DM Sans fonts, removes dead TopNav/PathBadge/SectionCard and prunes unused legacy CSS. Use proactively in wave 2 after B+C+D are merged.
---

You execute Phase E — brand and CSS cleanup.

## Branch

`cursor/ui-brand-cleanup-7a69` from the B+C+D integration branch.

## Exclusive ownership

| Edit | Do NOT edit |
|------|-------------|
| `client/src/styles.css` — remove unused `.btn`, `.topnav`, `.script-card`, `.history-*`, `.page-header`, `.empty-state`, `.status-*` blocks ONLY if no references remain | Page TSX logic |
| `client/index.html` — title, fonts | |
| Delete `client/src/components/TopNav.tsx` if unused | |
| Delete `client/src/components/ui/PathBadge.tsx`, `SectionCard.tsx` if no imports | |
| Brand strings: unify to **PromptPath** in AppSidebar, RunConsentStep, SettingsPage, EditForm copy | |

## Font rule

- Remove Geist `@import` from styles.css if DM Sans is canonical (keep Google Fonts link in index.html)
- Set `--font-sans` and shadcn body to DM Sans; `--font-mono` to IBM Plex Mono

## Verify

```bash
cd /workspace/client && npm run build
rg "PathBadge|SectionCard|TopNav" client/src --glob '*.tsx'  # should be empty
git push -u origin cursor/ui-brand-cleanup-7a69
```
