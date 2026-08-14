---
name: five-surface-ia
description: >
  Pathline four-surface IA (Dashboard, Path Library, Accounts, System).
  Sealed secrets live under Accounts (vaultStore). Use when restructuring
  client nav, embedding Edit/Run in Path Library, or Accounts secret binding.
  Structure-only; no restyle.
disable-model-invocation: true
---

# Pathline operator IA (four surfaces)

## Surfaces (only these)

| Nav label | `AppView.category` | Job |
|-----------|-------------------|-----|
| Dashboard | `dashboard` | Path status, quick actions, recent activity |
| Path Library | `paths` (+ `pathId`, `panel`) | List + detail; EditForm + Run embedded |
| Accounts | `accounts` (+ `accountId`) | Profiles + sealed secrets panel; fields bind `vaultKey` |
| System | `system` | Runtime health + former Settings |

**Removed:** workflows, edit, run, settings, Templates, Runs, and **Input Vault** as top-level views.

## Vocabulary

- UI: **Path**, sealed secrets (under Accounts), Step, When, Then, Input, Run
- Never write secrets into Path JSON
- `PRODUCT_TERMS` in `client/src/script/types.ts`
- Store: `vaultStore` remains; UI is Accounts → Sealed secrets

## Structure rules

- Flat four-item sidebar; no workflow tree
- Path Library = list + detail (not separate Edit/Run routes)
- No visual restyle in IA passes — layout/IA only
- Skill order: frontend-ui-architect → structure-redesign → this skill / implementation

## File map

- Nav: `client/src/navigation.ts`, `App.tsx`, `components/AppSidebar.tsx`
- Paths: `pages/PathsPage.tsx`, `pages/paths/*`
- Accounts: `pages/AccountsPage.tsx`, `pages/accounts/*`, `persistence/accountsStore.ts`
- Sealed secrets UI: `pages/vault/*` (embedded in Accounts), `persistence/vaultStore.ts`
- Dashboard: `pages/DashboardPage.tsx`, `pages/dashboard/*`
- System: `pages/SystemPage.tsx`, `pages/system/*`
- Readiness: `script/pathReadiness.ts` → `pathsAvailableForAccount`

## Acceptance

- Exactly four sidebar items
- Edit + dial only inside Path Library detail
- Account + vault unlocks matching Paths
- Client build + Vitest green
