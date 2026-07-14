---
name: desktop-scaffold
description: Scaffolds the Tauri desktop shell wrapping client/ with correct build paths and bundle id. Use proactively as wave 1 of desktop MVP — owns desktop/ only.
---

You scaffold the PromptPath Tauri desktop app.

## Workflow

```bash
cd /workspace
git checkout -b cursor/desktop-scaffold-7a69 origin/cursor/known-scripts-and-run-automation
cd desktop && npx tauri init --ci
```

## Requirements

- `frontendDist`: `../client/dist`
- `devUrl`: `http://localhost:3000`
- `beforeDevCommand`: `npm run dev --prefix ../client`
- `beforeBuildCommand`: `npm run build --prefix ../client`
- `identifier`: `com.promptpath.desktop`
- Window: 1280×800, title `PromptPath`
- `desktop/package.json` scripts: `dev`, `build`, `tauri`
- Root `package.json`: `desktop:dev`, `desktop:build`
- `desktop/.gitignore` excludes `node_modules/`

## Rules

- Do not implement SIP bridge or RunSession wiring — other agents own those
- Verify `cd desktop && npm run build` compiles after client build

## Output

Branch `cursor/desktop-scaffold-7a69` ready for RunSession and sidecar agents.
