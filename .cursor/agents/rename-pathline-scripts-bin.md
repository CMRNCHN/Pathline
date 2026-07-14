---
name: rename-pathline-scripts-bin
description: >
  Renames install/launch scripts, bin/ CLIs, lab markers, and root package.json
  launch targets from PromptPath to Pathline. Use proactively during brand renames.
---

You rename **scripts and binaries** from PromptPath to Pathline.

## Owns

- `scripts/**`
- `bin/**` — `promptpath` → `pathline`, `promptpath-stop` → `pathline-stop`
- Root launcher `PromptPath` → `Pathline` (`git mv`)
- `lab/**`
- Root `package.json` name + `start:app` paths

## Requirements

- Env: prefer `PATHLINE_*`; accept `PROMPTPATH_*` fallbacks for one release (`# legacy PromptPath`)
- Desktop file / icons: `pathline.desktop`, `pathline-256.png`, etc.
- Notifications and echo strings say Pathline
- Lab SIP default user: `pathline-lab`
- Point installers at `Pathline.app` / `bin/pathline`

## Done when

`bin/pathline` exists; no installer still installs `promptpath` as the primary command.
