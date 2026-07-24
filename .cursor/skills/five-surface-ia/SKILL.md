---
name: five-surface-ia
description: >
  Pathline five-surface IA (Dashboard, Path Library, Accounts, Input Vault,
  System). Use when restructuring client nav, embedding Edit/Run in Path
  Library, or working Accounts/Input Vault binding. Structure-only; no restyle.
disable-model-invocation: true
---

# Five-surface Pathline IA

## Surfaces (only these)

| Nav label | `AppView.category` | Job |
|-----------|-------------------|-----|
| Dashboard | `dashboard` | Status, quick actions, recent activity |
| Path Library | `paths` (+ `pathId`, `panel`) | List + detail; EditForm + Run embedded |
| Accounts | `accounts` (+ `accountId`) | Profiles; fields → path inputs; ready paths |
| Input Vault | `vault` | Sealed secret slots; Accounts bind `vaultKey` |
| System | `system` | Runtime health + former Settings |

**Removed:** workflows, edit, run, settings, Templates, Runs as top-level views.

## Vocabulary

- UI: **Path**, **Input Vault**, Step, When, Then, Input, Run
- Never write secrets into Path JSON
- `PRODUCT_TERMS` in `client/src/script/types.ts`

## Structure rules

- Flat five-item sidebar; no workflow tree
- Path Library = list + detail (not separate Edit/Run routes)
- No visual restyle in IA passes — layout/IA only
- Skill order: frontend-ui-architect → structure-redesign → this skill / implementation

## File map

- Nav: `client/src/navigation.ts`, `App.tsx`, `components/AppSidebar.tsx`
- Paths: `pages/PathsPage.tsx`, `pages/paths/*`
- Accounts: `pages/AccountsPage.tsx`, `pages/accounts/*`, `persistence/accountsStore.ts`
- Vault: `pages/VaultPage.tsx`, `pages/vault/*`, `persistence/vaultStore.ts`
- Dashboard: `pages/DashboardPage.tsx`, `pages/dashboard/*`
- System: `pages/SystemPage.tsx`, `pages/system/*`
- Readiness: `script/pathReadiness.ts` → `pathsAvailableForAccount`

## Acceptance

- Exactly five sidebar items
- Edit + dial only inside Path Library detail
- Account + vault unlocks matching Paths
- Client build + Vitest green
