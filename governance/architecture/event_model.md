# Event Model and Immutable Semantics

Operational Events are the primary source of truth in Pathline. They form an append-only, immutable log of all system activities.

## Immutable Semantics

1.  **Append-Only**: Once an event is written to the session log, it must NEVER be modified or deleted.
2.  **Canonical Ordering**: Events are ordered by `meta.timestamp`. The sequence in the `.jsonl` file reflects the authoritative timeline.
3.  **No In-Place Updates**: Any change to system state must be represented by a *new* event, not by modifying a previous one.

## Canonical Serialization

1.  **Format**: All events must be serialized as single-line JSON (JSONL).
2.  **Keys**: Mandatory top-level keys are `type`, `meta`, and `payload`.
3.  **Metadata**: The `meta` object must include `event_id`, `timestamp` (ISO-8601), and `session_id`.
4.  **Deterministic Serialization**: Keys in the JSON payload should be sorted (canonical JSON) to ensure that hash-based integrity checks (future) remain stable.

## Integrity and Validation

1.  **Schema Enforcement**: Events must be validated against their respective schemas (defined in `schemas/events/`) before being emitted by the `EventBus`.
2.  **Source Attribution**: Every event must have a `meta.source_component` indicating which part of the system generated it.
3.  **Payload Schema**: The `payload` must adhere to the specific structure defined for the given `type`.

## Versioning

1.  **Backward Compatibility**: The `replay` layer must remain capable of processing older event schemas.
2.  **Schema Versioning**: If a breaking change to an event structure is required, the `type` should be versioned (e.g., `TRANSCRIPT_FINAL_V2`) or a `schema_version` field added to `meta`.

## Performance and Scale

1.  **Bounded Payloads**: Avoid including large binary blobs in event payloads. Use references (e.g., `recording_reference`) instead.
2.  **Efficient Parsing**: Replay reconstruction relies on fast JSON parsing. Payloads should be kept lean.
