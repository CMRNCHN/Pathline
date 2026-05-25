# Replay Inspection — Developer Contract

---

## Canonical schema: `ReplayInspectionReport`

Defined in `replay/inspection_models.py`. All fields are frozen dataclasses.
`ReplayInspectionReport.to_dict()` / `.to_json()` serialize the full tree.

| Field | Type | Purpose |
|---|---|---|
| `schema_version` | `str` | Version string. Current value: `"1.0"`. |
| `identity` | `IdentitySection` | Session ID, call SID, source kind, source path. Used by CLI headers, API consumers, and UI routing. |
| `artifact_availability` | `ArtifactAvailabilitySection` | Per-artifact availability (`event_log`, `runtime_diagnostics`, `snapshots`, `recording`, `waveform`, `bookmarks`, `annotations`). Each entry has `artifact`, `available`, `location`, `detail`, `file_count`. |
| `session_metadata` | `SessionMetadataSection` | Envelope metadata: target, `started_at`, `ended_at`, `duration_ms`, `created_at`, `updated_at`. |
| `summary` | `SummarySection` | High-signal counts and text previews: `event_count`, `prompt_count`, `action_count`, `node_count`, `first_prompt`, `last_prompt`, `last_action`, `largest_gap_ms`, `notes`. |
| `chronology` | `ChronologySection` | Ordered `ChronologyEntry` list. Each entry: `seq`, `kind`, `t_ms`, `delta_ms`, `text`, `text_preview`, `event_id`, `node_id`, `dtmf`. |
| `path` | `PathSection` | Traversal data: `root_prompts`, `dtmf_path`, `unique_actions`, `visited_nodes`, `active_path`, `steps` (list of `PathStep`). |
| `state_diagnostics` | `StateDiagnosticsSection` | Runtime debug details: `graph_node_count`, `transcript_count`, `visited_node_count`, `call_status`, `snapshot_offset`, `target_offset`, `total_event_count`, `queue`, `metrics`, `error`. |
| `correlation` | `CorrelationSection` | Cross-artifact timing: `startup_to_gui_ready_ms`, `session_start_to_first_prompt_ms`, `session_start_to_first_action_ms`, `stream_connect_to_first_prompt_ms`, `session_duration_ms`, `last_activity_at`, `idle_for_s`. |
| `anomalies` | `list[Anomaly]` | Detected issues. Each `Anomaly` has `code`, `severity` (`"info"/"warn"/"error"`), `explanation`, `references`. |
| `bookmarks_annotations` | `BookmarksAnnotationsSection` | Operator-authored `BookmarkSummary` and `AnnotationSummary` lists. |
| `media_status` | `MediaStatusSection` | Recording and waveform availability and paths. |
| `next_steps` | `list[NextStep]` | Recommended operator actions. Each `NextStep` has `action`, `rationale`, `cites` (non-empty `list[Reference]`). |

### `Reference` type

`Reference` (in `inspection_models.py`) is a tagged pointer into the report or
a resolved artifact. Fields: `kind` (`ReferenceKind`), `label`, and optional
locators (`field_path`, `session_id`, `event_id`, `event_index`,
`media_time_ms`, `t_ms`, `snapshot_offset`, `artifact_path`, `value`).

---

## `schema_version` policy

Current version: **`"1.0"`**.

- **Additive changes** (new optional fields on any dataclass): keep `"1.0"`.
- **Breaking changes** (rename or remove any field, change a field's type):
  bump the version string and update this document.

Agents 2, 3, and 4 do **not** modify `replay/inspection_models.py` directly.
All schema changes must be escalated to Agent 1 (schema owner).

---

## Service contract

```python
# replay/inspection_service.py

def inspect_session(
    session_id: str,
    *,
    resolver: BundleResolver | None = None,
) -> ReplayInspectionReport: ...

# Alias used by replay_routes.py
build_inspection_report = inspect_session
```

- **Pure**: no I/O outside the `BundleResolver`. All network/filesystem access
  is encapsulated in `resolver.resolve(session_id)`.
- **Never raises on unknown sessions**: returns a report with
  `identity.source_kind == "empty"` when no artifacts exist. The HTTP route
  layer converts that signal to a 404.
- `InspectionService` is a thin class wrapper around `inspect_session` for
  callers that need an object interface:

  ```python
  class InspectionService:
      def __init__(self, resolver: BundleResolver | None = None) -> None: ...
      def inspect(self, session_id: str) -> ReplayInspectionReport: ...
  ```

---

## Compat shim: `replay/inspection.py`

`replay/inspection.py` is the legacy module. It continues to export all
pre-service functions unchanged:

- `inspect_replay_artifact(trace_source)` — inspects a raw trace file or
  event sequence; returns a plain dict (not a `ReplayInspectionReport`).
- `format_replay_inspection_text(payload)` — formats the legacy dict as text.
- `build_session_snapshot(...)` — constructs a session snapshot dict.
- `build_event_chronology(events)` — builds a chronology list from events.
- `build_runtime_diagnostics(runtime_metrics, ...)` — builds a runtime
  diagnostics dict.
- `format_runtime_diagnostics_text(payload)` — formats runtime diagnostics.
- `load_runtime_payload(metrics_path, runtime_url)` — loads a raw metrics dict.

The shim also re-exports the new service API:

```python
from replay.inspection import build_inspection_report, InspectionService
```

If `replay.inspection_service` is unavailable at import time, the shim falls
back to a `NotImplementedError` stub. Under normal operation, the real
implementation is always loaded.

Existing call sites that use any of the legacy functions do not need to change.

---

## Extending the schema

To add a **new optional field** to an existing section:

1. Add the field with a default value to the relevant dataclass in
   `replay/inspection_models.py` (Agent 1 only).
2. Populate it in the corresponding `_build_*` function in
   `replay/inspection_service.py`.
3. No `schema_version` bump required.

To **rename or remove** a field:

1. Bump `schema_version` in `ReplayInspectionReport` and update this document.
2. Update all consumers (CLI formatter in `replay/cli.py`, UI template,
   any downstream tests).

Agents 2, 3, and 4 must not edit `inspection_models.py`. File a schema change
request with Agent 1 and reference the field path and intended semantics.

---

## Anomaly detection

Located in `replay/anomaly_detection.py`. Both functions are currently stubs
that return empty lists:

```python
def detect_anomalies(report: ReplayInspectionReport) -> list[Anomaly]: ...
def generate_next_steps(report: ReplayInspectionReport) -> list[NextStep]: ...
```

`inspection_service.py` imports them and falls back to `lambda report: []` if
the import fails, so report construction is never blocked.

When Agent 3 ships real logic:

- `detect_anomalies` receives the fully-populated `ReplayInspectionReport`
  (excluding `anomalies` and `next_steps`) and returns `list[Anomaly]`.
- `generate_next_steps` receives the same partial report and returns
  `list[NextStep]`.
- **`NextStep.cites` must be non-empty** — this is enforced by
  `NextStep.__post_init__`. Every `NextStep` must cite at least one
  `Reference` that points to evidence in the report or the resolved artifacts.
  A `NextStep` with an empty `cites` list raises `ValueError` at construction.

The two STUB comments in `inspection_service.py` mark the exact call sites
Agent 3 must update.

---

## BundleResolver: injecting a custom resolver in tests

`BundleResolver` accepts optional service overrides for all five artifact
sources. Pass mocks or stubs to avoid filesystem and network access in tests:

```python
from replay.bundle_resolver import BundleResolver
from replay.inspection_service import inspect_session

resolver = BundleResolver(
    replay_service=my_fake_replay_service,
    snapshot_service=my_fake_snapshot_service,
    media_replay_service=my_fake_media_service,
    bookmark_service=my_fake_bookmark_service,
    annotation_service=my_fake_annotation_service,
)
report = inspect_session("test-session-id", resolver=resolver)
```

Each service defaults to its production singleton when not provided.
`ResolvedReplayBundle` is a frozen dataclass — you can also construct it
directly and pass it to `_build_report` in unit tests that bypass the resolver
entirely:

```python
from replay.bundle_resolver import ResolvedReplayBundle
from replay.inspection_service import _build_report

bundle = ResolvedReplayBundle(session_id="test-session-id", raw_events=[...])
report = _build_report(bundle)
```

`_build_report` is not part of the public API (prefixed `_`) but is stable
enough for internal test use.
