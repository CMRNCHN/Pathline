# Replay Inspection Task Docs

Per-agent task definitions for the replay inspection productization pass.

## How to use

Every Air task (or Claude Code session) is launched with a one-line
prompt pointing at the relevant doc:

> Read `docs/agent-tasks/replay-inspection/<role>.md` and execute it.

The task doc holds the role-specific instructions. AGENTS.md at the repo
root holds shared rules, the file-ownership table, and the definition of
done — every task doc references it.

## Workflow order

1. **Batch 1 (serial):** `agent-1-schema.md` — runs alone.
2. **Batch 2 (parallel):** `agent-2-cli-api.md`, `agent-3-anomalies.md`,
   `agent-4-ui.md` — three concurrent worktrees off the feature branch
   updated with Agent 1's merged work.
3. **Batch 3 (serial):** `agent-5-validation.md` — runs alone after
   2, 3, 4 all merge.

Do not start Batch 2 until Agent 1's schema is merged. Do not start
Batch 3 until Agents 2, 3, 4 are all merged.

## Status field

Each task doc has a `Status:` line near the top. The human operator
updates it manually as work progresses. It is not enforced by tooling;
its purpose is to give anyone reading the repo a quick read on workflow
state without digging through PRs or chat history.

Status vocabulary:

- `ready` — task is defined but not yet started
- `running` — agent session in progress in a worktree
- `awaiting-review` — agent has stopped and surfaced for human review
- `merged` — work has landed on the feature branch
- `blocked` — agent or human has escalated; not progressing

For multi-deliverable tasks (Agent 1 has four), use suffixes:

- `deliverable-1-running`
- `deliverable-1-merged, deliverable-2-running`
- `deliverable-1-merged, deliverable-2-merged, deliverable-3-running`
- etc.

When the human flips status, they commit the change to the feature
branch so the marker is visible to any subsequent worktree.

## Branch convention

Worktree branches for this pass follow:

```
next/replay-and-runtime-usability--agent-<N>[-d<deliverable>]
```

Examples:

- `next/replay-and-runtime-usability--agent-1-d1`
- `next/replay-and-runtime-usability--agent-1-d2`
- `next/replay-and-runtime-usability--agent-2`
- `next/replay-and-runtime-usability--agent-3`
- `next/replay-and-runtime-usability--agent-4`
- `next/replay-and-runtime-usability--agent-5`

Each branch is created off the current tip of
`next/replay-and-runtime-usability` and merged back via squash-merge PR.

## Cleanup

When this pass is complete, this directory can be deleted. The
information is preserved in PR descriptions and git history. Or keep it
as a template for the next pass — your call.
