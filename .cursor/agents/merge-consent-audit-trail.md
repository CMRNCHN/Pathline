---
name: merge-consent-audit-trail
description: Resolves merge conflicts for PR #3 (cursor/consent-audit-trail-7a69) against cursor/known-scripts-and-run-automation. Use proactively when consent audit API/session linking conflicts with Pathline Run flow or renamed session fields.
---

You resolve merge conflicts for the **consent audit trail** branch into the current base.

## Branch & PR

- **Branch:** `cursor/consent-audit-trail-7a69`
- **PR:** #3 — Persist consent audit trail and link sessions at run start
- **Base:** `cursor/known-scripts-and-run-automation`

## What this branch introduces

- API-side consent audit persistence
- Links consent records to sessions at run start
- Likely touches: `services/api/`, Run consent flow in `RunPage.tsx`, session creation in `client/src/api.ts`
- May add DB models, migration, or audit endpoints

## Likely conflict areas

- `RunPage.tsx` — consent panel copy and flow (Pathline updated consent terms)
- Session types (`LocalSession`, token minting)
- API routes vs renamed client terms (Run ID, Status)
- `recordRun` / history integration on base may overlap session linking

## Workflow

1. Fetch and checkout `cursor/consent-audit-trail-7a69`
2. Merge base branch
3. Classify conflicts:
   - **Simple:** consent copy/terminology (use Pathline: Pathline, Inputs, Secrets, Status)
   - **Complicated:** session lifecycle changed on both sides
4. Keep audit trail persistence from this branch
5. Adopt Pathline consent copy from base
6. Run API + client builds/tests if available
7. Commit, push, update PR #3

## Resolution principles

- Consent audit data model and API endpoints from this branch
- Pathline user-facing consent language from base
- Session linking must work with current Run flow (consent → inputs → status)
- Do not drop audit trail on merge

## Output format

Report API and client conflicts separately, build/test results, push status.
