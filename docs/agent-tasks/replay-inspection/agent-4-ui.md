# Agent 4 — analyst UI workflow

Status: ready
Branch: next/replay-and-runtime-usability--agent-4 (when started)
Worktree: ../pathline-agent-4 (when started)

You own the operator UI experience for replay inspection. You do not
own data shape.

You may not start until Agent 1's Deliverables 1, 2, 3, and 4 are all
merged to `next/replay-and-runtime-usability`. You may start in
parallel with Agent 2 and Agent 3 — Agent 2's API route is what your
page fetches from, but you can develop against the schema shape
directly and stub the fetch if needed. The final integration must
consume the real route.

Read AGENTS.md at the repo root before doing anything.

## Stack

Server-rendered Jinja templates plus vanilla JS. No React. No build
step. No component framework. Follow the existing analyst UI
conventions exactly. The repository's analyst UI is a Flask app
serving Jinja templates with static JS and CSS — do not introduce a
new frontend pattern.

## Files you own (new)

- `analyst/frontend/templates/replay_inspection.html`
- `analyst/frontend/static/js/replay_inspection.js`
- `analyst/frontend/static/css/replay_inspection.css` (optional; prefer
  extending existing CSS if there's a natural place)
- A route registration for the page itself (e.g., `GET /replay-inspection`
  returning the template) in the appropriate analyst route file.

The page route lives in `analyst/backend/routes/replay_routes.py`.
Agent 2 owns the *API* route (`GET /api/replay-inspection/{session_id}`)
in the same file. Coordinate so you do not stomp on each other:

- Agent 2's PR lands first if possible — the API route is what you
  need for end-to-end testing.
- If both PRs are open at once, the second-merged rebases on the
  first-merged. Air's diff review and GitHub conflict markers will
  surface any collision.

## Files you may read but not modify

- `analyst/frontend/templates/index.html`
- `analyst/backend/ui/template_loader.py`
- `analyst/backend/ui/ui_state.py`
- Existing files in `analyst/frontend/static/css/` and
  `analyst/frontend/static/js/`

You may add an additive navigation entry pointing at the new page in
whatever shared template hosts navigation — that is the *only*
permitted edit outside your ownership column. If the navigation entry
requires changing more than a single line or two, escalate.

## Required reading before edits

- `analyst/frontend/templates/index.html` to learn the layout
  conventions, block structure, CSS class naming.
- `analyst/backend/ui/template_loader.py` and `ui_state.py` to learn
  how templates get rendered and what context they receive.
- Existing CSS and JS under `analyst/frontend/static/` to match style.
- `analyst/backend/routes/replay_routes.py` to see existing route
  patterns and identify where to add yours.
- `replay/inspection_models.py` to know the report shape your page
  renders.

## Tasks

### Page route

Add a route (e.g., `GET /replay-inspection?session_id=<id>` or
`/replay-inspection/<session_id>` — match the convention used by
existing analyst pages) that renders `replay_inspection.html`.

The route passes the session id and any minimal page-level context
into the template. **The route must not fetch the report itself** —
the page does that client-side via Agent 2's API route. This keeps
the canonical report fetch path single-purpose.

### Template

`replay_inspection.html` renders the page shell:

- Header with session id and a fetch indicator
- Containers for each report section the JS will populate:
  - Summary card
  - Anomalies list (color-coded by severity)
  - Chronology / timeline
  - Prompt-and-action path
  - State / media diagnostics
  - Next steps
- Loading and error states

Use the same template inheritance, block structure, and CSS classes as
existing analyst pages.

### JavaScript

`replay_inspection.js`:

- On page load, reads the session id from the URL (query string or
  path).
- Calls `GET /api/replay-inspection/{session_id}` (Agent 2's route).
- Parses the JSON response (which is the canonical
  `ReplayInspectionReport` payload).
- Populates each container in the template directly from the payload —
  **no client-side reshaping, no client-side anomaly detection, no
  client-side next-step generation**.
- Renders anomalies with severity-based color coding (`info`/`warn`/
  `error` map to consistent colors — pick from existing CSS if there's
  a convention).
- Renders next steps as clickable items. Each next step's `cites`
  array contains `Reference` objects with `field_path`, `event_index`,
  `t_ms`, etc. Clicking a next step scrolls or links to the cited
  report field on the same page. Use the `field_path` for anchor IDs
  on the rendered fields.
- Surfaces missing artifacts from `artifact_availability.missing`
  visibly — operators need to know what's not available, not just
  see empty sections.

### Grounding-as-UX

The next-step grounding rule isn't just a contract requirement, it's a
UX feature. When an operator sees "Inspect audio around 12.4s," they
should be able to click and land at the chronology entry being cited.
The `Reference` model includes `field_path`, `event_index`, `t_ms`,
and other anchors — use them.

If a next step renders without a working link, that's a bug. Either
the next step shouldn't have been emitted (Agent 3's problem, escalate
back through review), or the anchor logic is broken (your problem).

## Constraints

- No bespoke payload shape. No client-side anomaly detection or
  next-step generation. If the report doesn't have it, you don't
  render it.
- No CSS refactors on existing pages. No JS refactors on existing
  pages. No template restructuring beyond your own new files.
- Scope is tightly bounded to this flow. Navigation/menu changes are
  allowed only as additive entries.
- Final summary follows AGENTS.md: What changed / Why / Risks /
  Validation status / Removed/Moved / Touched outside ownership.

## Final validation

Run before reporting done:

```
pytest tests/ -q
```

Plus a manual smoke check:

- Start the analyst backend locally.
- Navigate to your new page with a known session id.
- Verify the page renders, fetches the report, and all six sections
  populate.
- Click a next step. Verify it scrolls or links to the cited field.
- Try a session id with missing artifacts. Verify the missing artifacts
  surface visibly and the page does not crash.

Document the manual smoke check in your final summary's validation
status section. If you can't run the backend locally (env issues,
etc.), say so explicitly — don't claim manual smoke without doing it.
