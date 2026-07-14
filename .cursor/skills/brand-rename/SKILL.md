---
name: brand-rename
description: >
  Safely rename a product/brand string across a codebase (display name, packages,
  binaries, docs, agents, env keys, persistence) while auditing pre- and
  post-rename conflicts. Use when the user asks to rename an app/brand, migrate
  PromptPath→Pathline or any old→new product name, or when leftover old brand
  strings appear after a rename. Use proactively after UI vocabulary or brand
  decisions land.
---

# Brand Rename

Reusable conflict-aware rename for app/program names (not file-path URLs).

## Default mapping (this repo)

| Kind | Old | New |
|------|-----|-----|
| Display | `PromptPath` | `Pathline` |
| slug / npm / cargo | `promptpath` | `pathline` |
| Python package | `promptpath_*` | `pathline_*` |
| Env prefix | `PROMPTPATH_` | `PATHLINE_` |
| Bundle id | `com.promptpath.*` / `dev.promptpath.*` | `com.pathline.*` / `dev.pathline.*` |
| SIP bridge | `__promptpathSipBridge` | `__pathlineSipBridge` |

Do **not** invent alternate brand spellings. Product vocabulary (Workflow / Path / Run) is orthogonal — keep those rules from `client/src/script/types.ts`.

## Conflict window (time)

| Window | What to check | Why |
|--------|---------------|-----|
| **Look-back: 30 days** of git history + all open PRs/branches matching `*rename*`, `*pathline*`, `*promptpath*` | Conflicting renames, half-applied migrations, dual package names | Renames land in waves; older branches reintroduce old tokens |
| **Look-ahead: 14 days** after merge (or until zero new hits) | CI logs, new agent PRs, `rg` on `main` nightly / next agent run | Catch regressions from merges that still say the old name |
| **Hard stop** | Zero matches for old display name outside the **compat allowlist** | Rename incomplete until allowlist-only |

Record the window start as merge commit date. Re-run the verify agent until look-ahead expires with no new hits.

## Phase checklist

Copy and track:

```
Brand rename progress:
- [ ] 0. Scope — old→new table + allowlist
- [ ] 1. Look-back conflict audit (30d)
- [ ] 2. Inventory (`rg -i` file list by zone)
- [ ] 3. Execute zone agents (docs / client / desktop / python / scripts / cursor agents)
- [ ] 4. Compat shims (storage, env, bridge alias if needed)
- [ ] 5. Verify sweep (allowlist-only leftovers)
- [ ] 6. Schedule look-ahead re-verify (14d)
```

### 0. Scope

1. Confirm display name, slug, package prefix, env prefix, bundle id.
2. Build **compat allowlist** (things that may keep the old token temporarily):
   - Migration readers for old localStorage / IndexedDB names
   - One-release env fallbacks (`PATHLINE_*` preferred, `PROMPTPATH_*` accepted)
   - Comments that say `legacy PromptPath key` next to the shim
3. Everything else must become the new name.

### 1. Look-back conflict audit (30 days)

```bash
# Branches / PRs that may fight this rename
git log --since='30 days ago' --oneline --all --grep='rename\|Pathline\|PromptPath' -i
git branch -a | rg -i 'rename|pathline|promptpath'

# Open PR titles (if gh available)
gh pr list --search 'PromptPath OR Pathline OR rename' --limit 30
```

If another rename is in flight with a **different** target name, stop and reconcile. If same target, rebase onto it.

### 2. Inventory by zone

```bash
rg -i -l 'promptpath|PromptPath|PROMPTPATH' \
  --glob '!.git' --glob '!node_modules' --glob '!**/target/**' \
  --glob '!**/dist/**' --glob '!**/*lock*'
```

Partition hits into zones owned by the subagents in `.cursor/agents/rename-pathline-*.md`.

### 3. Execute (prefer subagents)

Run in parallel when ownership does not overlap:

| Agent | Owns |
|-------|------|
| `rename-pathline-docs` | README, docs/, architecture md |
| `rename-pathline-client` | `client/`, `frontend-ui/`, user-facing + persistence keys |
| `rename-pathline-desktop` | `desktop/`, `.app` bundles, Tauri id/title |
| `rename-pathline-python` | `packages/`, `services/`, docker module paths |
| `rename-pathline-scripts-bin` | `scripts/`, `bin/`, lab, installers |
| `rename-pathline-cursor-agents` | `.cursor/agents/`, plans, cloud notes |

Use `git mv` for directories/files whose **names** contain the old brand.

### 4. Compat shims (required for persistence / env)

- Prefer new keys; **read old then new** once; write only new.
- Env: `PATHLINE_FOO="${PATHLINE_FOO:-${PROMPTPATH_FOO:-default}}"`.
- Optional one-release JS alias: `window.__pathlineSipBridge ??= window.__promptpathSipBridge`.
- Mark every shim with `// legacy PromptPath` / `# legacy PromptPath` so the verify agent can allowlist them.

### 5. Verify sweep

Delegate to `rename-pathline-verify` or run:

```bash
rg -i 'promptpath|PromptPath|PROMPTPATH' \
  --glob '!.git' --glob '!node_modules' --glob '!**/target/**' \
  --glob '!**/dist/**' --glob '!**/*lock*'
```

Fail if any hit is outside the compat allowlist / legacy-marked shim.

Also smoke:

- Client typecheck / build
- API import path (`pathline_api` / `pathline_shared`)
- Desktop `productName` / identifier

### 6. Look-ahead (14 days)

After merge, any agent touching this repo in the next **14 days** must:

1. Re-run the verify `rg` before finishing brand-sensitive work.
2. If old tokens reappear from a merge, fix forward in that PR — do not reopen a mega-rename unless hits exceed ~20 files.

## Anti-patterns

- Renaming only UI copy while leaving `productName`, binaries, and Python packages on the old brand
- Changing GitHub remote / cloud environment ids without user request (repo URL may lag the product name)
- Blind `sed` on lockfiles — regenerate locks after package renames instead
- Treating Workflow/Path/Run vocabulary as brand names (see types.ts contract)

## Additional resources

- Zone details and ownership rules: [zones.md](zones.md)
- Compat allowlist template: [compat-allowlist.md](compat-allowlist.md)
