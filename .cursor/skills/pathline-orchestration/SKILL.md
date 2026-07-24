---
name: pathline-orchestration
description: >
  Orchestrates Pathline multi-agent delivery with exclusive file lanes,
  phase gates, and Figma-vs-code separation. Use when coordinating parallel
  work, preventing edit overlap, or starting Figma + client waves together.
disable-model-invocation: true
---

# Pathline orchestration

## Principle

One **orchestrator** assigns work. Each lane has **exclusive paths**. No two agents edit the same files in one wave.

## Invoke

1. Start with agent **`pathline-orchestrator`**.
2. Orchestrator picks lanes from the map below and states exit criteria.
3. Specialists run; orchestrator verifies gates before the next wave.

## Exclusive lanes

| Lane | Agent | Paths |
|------|-------|-------|
| Figma | `pathline-figma-design` | Figma MCP only |
| Nav/shell | `five-surface-nav-shell` | `client/src/navigation.ts`, `App.tsx`, `components/AppSidebar.tsx`, `components/Shell.tsx` |
| Paths | `five-surface-path-library` | `client/src/pages/PathsPage.tsx`, `pages/paths/**`, Edit/Run embed wiring |
| Accounts/Vault | `five-surface-accounts-vault` | `pages/AccountsPage.tsx`, `pages/accounts/**`, `pages/VaultPage.tsx`, `pages/vault/**`, `persistence/accountsStore.ts`, `persistence/vaultStore.ts`, `script/pathReadiness.ts` |
| Dash/System | `five-surface-dashboard-system` | `pages/DashboardPage.tsx`, `pages/dashboard/**`, `pages/SystemPage.tsx`, `pages/system/**` |
| UX upgrade | `pathline-ux-upgrade` | Same client areas as upgrade brief; **serialize** vs surface agents if paths overlap |

## Parallelism that is safe

- Figma Foundations **∥** any single client lane
- Path Library **∥** Accounts/Vault (disjoint files)
- Never Path Library **∥** UX-upgrade Path list work

## Phase gates

| Gate | Required |
|------|----------|
| After Figma screens | File URL + page checklist from figma agent |
| After each client wave | `cd client && npm run build && npm test` |
| Before keyring | Accounts/Vault on IndexedDB |
| Before lab SIP polish | Five-surface UX upgrade P0 done |

## Figma free

See [pathline-figma-mcp](../pathline-figma-mcp/SKILL.md). Orchestrator must **not** assign Code Connect / Dev Mode / published library work on free/Starter.
