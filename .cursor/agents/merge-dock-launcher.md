---
name: merge-dock-launcher
description: Resolves merge conflicts for PR #6 (cursor/dock-launcher-7a69) against cursor/known-scripts-and-run-automation. Use proactively when macOS/Linux dock launcher, app icon, or install script changes conflict with Pathline renames.
---

You resolve merge conflicts for the **dock launcher** branch into the current base.

## Branch & PR

- **Branch:** `cursor/dock-launcher-7a69`
- **PR:** #6 — Dock launcher with custom PromptPath icon
- **Base:** `cursor/known-scripts-and-run-automation`

## What this branch introduces

- Custom app icon generation (`scripts/generate-app-icon.py`, `assets/icon/`)
- macOS `.app` bundle / dock pinning
- Linux desktop entry and GNOME dock install (`install-linux-desktop.sh`)
- `icnsutil` conditional install (macOS only); Pillow for Linux
- Brand references may still say "PromptPath" — Pathline rebrand may apply to display names only

## Likely conflict areas

- `.gitignore` — icon generated file rules
- `package.json` / `scripts/start.sh` — app name or open commands
- `scripts/build-macos-app.sh`, install scripts
- Any README or notification strings referencing "Scripts" vs "Paths"

## Workflow

1. `git fetch origin cursor/known-scripts-and-run-automation cursor/dock-launcher-7a69`
2. `git checkout cursor/dock-launcher-7a69`
3. Merge base branch
4. Classify conflicts (simple rename vs competing install behavior)
5. Keep launcher functionality; adopt Pathline display name where user-facing ("Pathline" not "PromptPath" in notifications if base changed this)
6. Verify icon scripts still run on Linux without `icnsutil`
7. Test: `./scripts/generate-app-icon.py` (if applicable), `cd client && npm run build`
8. Commit, push, update PR #6

## Resolution principles

- Launcher/install mechanics from this branch take priority
- Pathline terminology for user-visible strings from base
- Do not break cross-platform icon generation (Linux must not require icnsutil)
- Preserve `.gitignore` rules for generated icon intermediates

## Output format

Report conflicts fixed, any complicated merges, build/script test results, and push status.
