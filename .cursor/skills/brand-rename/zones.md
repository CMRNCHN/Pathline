# Brand rename zones

Ownership boundaries for parallel subagents. Do not edit outside your zone unless verifying.

## docs

- `README.md`
- `docs/**`
- `*Architecture*.md`
- Root launcher comments that are documentation-only

## client

- `client/**` (except build artifacts)
- `frontend-ui/**`
- Persistence keys, export filenames, theme keys, IndexedDB name
- SIP bridge consumer (`SipTransport`) — new name + optional alias read

## desktop

- `desktop/**`
- `PromptPath.app` / `PromptPath Stop.app` → `Pathline.app` / `Pathline Stop.app`
- Tauri `productName`, window title, `identifier`, Cargo package name

## python

- `packages/shared-python/**` (`promptpath_shared` → `pathline_shared`)
- `services/**` (`promptpath_api` → `pathline_api`, FastAPI titles, pyproject names)
- `docker-compose.yml` module + DB path strings
- Import updates + egg-info regeneration as needed

## scripts-bin

- `scripts/**`
- `bin/promptpath*` → `bin/pathline*`
- Root `PromptPath` launcher script → `Pathline`
- `lab/**` markers and default SIP user
- Root `package.json` script paths

## cursor-agents

- `.cursor/agents/**`
- Future plans under `docs/plans/**` that instruct agents
- Skill cross-links that still say the old brand as the *current* name
