# Replay Inspection — Operator Guide

Replay inspection loads all artifacts for a session (event log, runtime state,
snapshots, media, bookmarks, annotations) and returns a structured report.
Three entry points produce the same data: CLI, HTTP API, and browser UI.

---

## CLI

### inspect-session

```
pathline inspect-session --session-id <id>
pathline inspect-session --session-id <id> --format json
```

`--format` accepts `text` (default) or `json`.

**Text output shape**

```
Replay inspection report
  schema_version: 1.0

Identity
  session_id: abc123
  call_sid:   CA...
  source:     event_log

Missing artifacts: snapshots, recording

Summary
  event_count:   42
  prompt_count:  7
  action_count:  5
  first_prompt:  Press 1 for billing
  last_action:   dtmf:1
  largest_gap_ms: 3200

  dtmf_path: 1 → 2 → 3
  visited_nodes: 4

Anomalies (0)

Next steps (0)
```

**JSON output shape** (top-level keys)

```json
{
  "schema_version": "1.0",
  "identity": { "session_id": "...", "call_sid": "...", "source_kind": "event_log", "source_path": null },
  "artifact_availability": { "entries": [...], "missing": [...] },
  "session_metadata": { "target": "...", "started_at": ..., "ended_at": ..., "duration_ms": ..., ... },
  "summary": { "event_count": 42, "prompt_count": 7, "action_count": 5, ... },
  "chronology": { "entries": [ { "seq": 1, "kind": "prompt", "t_ms": 0, "delta_ms": 0, "text": "...", "text_preview": "..." }, ... ] },
  "path": { "root_prompts": [...], "dtmf_path": [...], "unique_actions": [...], "visited_nodes": [...], "active_path": [...], "steps": [...] },
  "state_diagnostics": { "graph_node_count": 8, "call_status": "completed", ... },
  "correlation": { "session_start_to_first_prompt_ms": 120, "session_duration_ms": 31400, ... },
  "anomalies": [],
  "bookmarks_annotations": { "bookmarks": [...], "annotations": [...] },
  "media_status": { "recording_available": false, "waveform_available": false, ... },
  "next_steps": []
}
```

### inspect-replay (legacy artifact path)

Inspects a raw trace file directly, without session storage lookup.

```
pathline inspect-replay --trace-path /path/to/trace.json
pathline inspect-replay --trace-path /path/to/trace.json --format json
```

---

## HTTP API

```
GET /api/replay-inspection/{session_id}
```

Returns a JSON object with the same shape as `--format json` above.

**Success (200)**

Content-Type: `application/json`. Body is the serialized `ReplayInspectionReport`.

**Session not found (404)**

```json
{"error": "session not found: <session_id>"}
```

A 404 is returned when no event log or snapshot exists for the session.
The bundle resolver never raises on unknown sessions — a 404 is signaled by
`identity.source_kind == "empty"` inside the route handler.

---

## Browser UI

```
http://localhost:<port>/replay-inspection?session_id=<id>
```

The server reads `?session_id` from the query string and injects it as boot
data into the HTML template (`replay_inspection.html`). The page then calls
`GET /api/replay-inspection/{session_id}` to load the report.

Sections shown in the UI correspond directly to the report's top-level fields:

- **Identity** — session ID, call SID, source kind
- **Artifact availability** — which artifacts resolved and which are missing
- **Summary** — event/prompt/action counts, first prompt, largest gap
- **Chronology** — ordered event timeline with timestamps and deltas
- **Path** — DTMF path, visited nodes, step-by-step traversal
- **State diagnostics** — graph node count, call status, snapshot offset
- **Correlation** — timing deltas between session start, first prompt, first action
- **Anomalies** — detected issues (none until Agent 3 ships real logic)
- **Bookmarks & Annotations** — operator-authored markers
- **Media status** — recording and waveform availability
- **Next steps** — recommended operator actions (none until Agent 3 ships)

---

## Workflow example: diagnosing a failed session

**Goal**: understand why session `abc123` ended without a final action.

1. Run the CLI to get a quick text summary:

   ```
   pathline inspect-session --session-id abc123
   ```

   Check `action_count` in the Summary section. If it is 0, no action was taken.

2. Check artifact availability in the output header:

   ```
   Missing artifacts: recording, waveform
   ```

   Missing media is expected for failed calls. Missing `runtime_diagnostics`
   means state could not be reconstructed — investigate storage.

3. Get the full JSON for deeper analysis:

   ```
   pathline inspect-session --session-id abc123 --format json > abc123.json
   ```

4. Inspect the `chronology` array. Look for the last event — if it is
   `call_ended` or `error` with no preceding `action` event, the session
   terminated before any DTMF or speech was sent.

5. Check `correlation.session_start_to_first_prompt_ms`. A very large value
   (or null) means the IVR either did not prompt the caller or the transcript
   was not captured.

6. Check `state_diagnostics.call_status`. Values like `failed` or `busy`
   indicate the call did not connect properly.

7. Open the browser UI for a visual overview:

   ```
   http://localhost:8080/replay-inspection?session_id=abc123
   ```

   Review the Chronology and Path sections side-by-side to confirm whether
   the path stalled at a known IVR node.

8. If bookmarks or annotations exist (`bookmarks_annotations` section), review
   them for prior operator notes on the same session.
