---
name: shadcn-shell-sidebar
description: Replaces TopNav with shadcn Sidebar layout (AppSidebar, Shell, SidebarInset). Use proactively after brand/paths/run branches are pushed — wave 2 of parallel shadcn migration; owns shell files only.
---

You replace the legacy top navigation with a shadcn Sidebar app shell.

## Branch

Work on `cursor/shadcn-shell-7a69` branched from `cursor/shadcn-setup-7a69` (after wave 1 branches are pushed).

```bash
cd /workspace
git fetch origin cursor/shadcn-setup-7a69
git checkout -b cursor/shadcn-shell-7a69 origin/cursor/shadcn-setup-7a69
```

## File ownership (exclusive)

| May edit | Must NOT edit |
|----------|---------------|
| `client/src/components/Shell.tsx` | `PathsPage.tsx`, `RunPage.tsx`, `styles.css` |
| `client/src/components/TopNav.tsx` (deprecate or gut) | Page bodies, run engine, transport |
| New `client/src/components/AppSidebar.tsx` | |
| Minimal layout in `client/src/App.tsx` (pass search props only) | View state machine in App.tsx |

## Target structure

```
SidebarProvider (wrap in Shell or App — TooltipProvider already in main.tsx)
  AppSidebar — brand, Paths, History, Settings, Import
  SidebarInset
    optional context bar: path name + Edit/Run tabs when path open
    {children}
```

## AppSidebar requirements

Use components from `client/src/components/ui/sidebar.tsx`:
- Brand: Pathline + Radio icon → navigate to paths
- Nav items: Paths (GitBranch), History (Clock)
- Footer: Settings (gear), Import (file upload — move logic from TopNav)
- Paths search: `SidebarInput` or header strip in SidebarInset when `view.category === "paths"`

## TopNav migration

Move from `TopNav.tsx` into AppSidebar + context bar:
- Import JSON handler (hidden file input + `importScript`)
- Search query controlled from App via Shell props
- Context row: path name + Edit/Run tabs when `view.category === "edit" | "run"`

## Constraints

- Do not change `AppView` navigation types or `onNavigate` contract
- Do not modify page components
- `main.tsx` already has `TooltipProvider` — add `SidebarProvider` in Shell.tsx

## Workflow

1. Create `AppSidebar.tsx`, refactor `Shell.tsx`
2. Gut or remove `TopNav.tsx` imports
3. Minimal `App.tsx` changes if needed for search placement
4. Run `cd /workspace/client && npm run build`
5. Commit: `Replace TopNav with shadcn Sidebar shell`
6. Push: `git push -u origin cursor/shadcn-shell-7a69`
