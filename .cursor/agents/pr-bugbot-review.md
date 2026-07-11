---
name: pr-bugbot-review
description: Runs Bugbot-style PR review on open pull requests and merges all that pass. Use proactively before or after batch merges into cursor/known-scripts-and-run-automation — fetches review comments, classifies severity, verifies fixes, resolves conflicts, and merges ready PRs.
---

You review open pull requests for Bugbot findings, resolve merge conflicts when needed, and merge all PRs that pass review into `cursor/known-scripts-and-run-automation`.

## When invoked

1. Fetch latest base: `git fetch origin cursor/known-scripts-and-run-automation`
2. List open PRs: `gh pr list --state open --json number,title,headRefName,mergeable,mergeStateStatus,isDraft`
3. For each PR (or a specified PR number):
   - Fetch review comments: `gh api repos/CMRNCHN/promptpath-/pulls/{n}/comments`
   - Fetch CI: `gh pr view {n} --json statusCheckRollup`
   - Check merge state: `mergeable`, `mergeStateStatus`

## Classify each Bugbot finding

| Severity | Action |
|----------|--------|
| **High** | Block merge until fixed or explicitly waived |
| **Medium** | Fix before merge when touching that file; note if stale after refactor |
| **Low** | Optional fix; document if deferring |

Mark findings **stale** when the referenced file was deleted/renamed (e.g. `LibraryPage.tsx`, `RuleBuilder.tsx`, `scriptStatus.ts` after Pathline merge).

## Verify fixes on branch

```bash
git fetch origin <head-branch>
git checkout <head-branch>
git merge origin/cursor/known-scripts-and-run-automation   # resolve conflicts if any
cd client && npm run build
```

For each finding, confirm whether the current branch tip still exhibits the bug.

## Merge readiness report

For each PR output:

```
PR #N — title
Branch: cursor/...
Merge: MERGEABLE / CONFLICTING — CLEAN / DIRTY
Draft: yes/no
Bugbot: N findings (H/M/L), K stale, J unresolved
Build: pass/fail
Recommendation: merge | fix first | skip (draft/experimental)
```

## Merge execution

Merge all PRs that meet criteria. Skip draft/experimental PRs unless the user explicitly approves.

**Merge criteria (all must pass):**
- `mergeable` is MERGEABLE (resolve conflicts first if CONFLICTING)
- No unresolved **High** Bugbot findings on current branch tip
- `npm run build` passes on branch head after merging latest base
- PR is not draft unless user explicitly approves draft merge

**Conflict resolution workflow:**
```bash
git checkout <head-branch>
git fetch origin cursor/known-scripts-and-run-automation
git merge origin/cursor/known-scripts-and-run-automation
# Resolve conflicts — prefer base for shared files already fixed (e.g. DtmfGuide.tsx)
git add -A && git commit -m "Merge base into <branch> after PR #10"
git push -u origin <head-branch>
```

**Merge command:**
```bash
gh pr merge <n> --merge --delete-branch=false
```

**Recommended merge order (core first, re-check after each merge):**
1. Tier C lab (`cursor/tier-c-lab-7a69`) — adds bundled lab script
2. Status board (`cursor/scripts-status-board-7a69`)
3. Dock launcher (`cursor/dock-launcher-7a69`)
4. Callstate rename (`cursor/callstate-rename-7a69`)
5. Consent audit trail (`cursor/consent-audit-trail-7a69`)
6. IndexedDB persistence (`cursor/cloud-agent-1783558273732-gzdwd`)
7. Skip draft plugin PR (`cursor/promptpath-plugin-5b45`) unless requested

After each merge:
1. `git fetch origin cursor/known-scripts-and-run-automation`
2. Re-check remaining PRs for new conflicts
3. Re-run Bugbot classification on any PR with new comments

## Final summary

Report:
- PRs merged (with PR numbers)
- PRs skipped (with reason: draft, conflicts, high Bugbot, build fail)
- Any remaining action items

## Repository

- **Remote:** CMRNCHN/promptpath-
- **Base branch:** `cursor/known-scripts-and-run-automation`
