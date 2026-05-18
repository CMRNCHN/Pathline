# Snapshot Semantics and Invariants

Snapshots in Pathline are deterministic checkpoints of the `ReplayState`. They allow for high-performance session reconstruction without needing to process the entire event stream from the beginning of time.

## Snapshot Invariants

1.  **Offset Integrity**: A snapshot at `event_offset` N must exactly represent the state after the Nth event in the canonical event stream has been applied.
2.  **State Completeness**: A snapshot must contain all necessary data structures (`nodes`, `edges`, `transcripts`, `metrics`, `active_path`, `visited_nodes`) required to resume replay.
3.  **Immutability**: Once persisted, a snapshot is immutable. Any changes to state logic that affect reconstruction must result in new snapshot versions or invalidation of old ones.
4.  **No Side Effects**: Creating or loading a snapshot must not trigger any runtime side effects (e.g., dialing, recording).

## Reconstruction Guarantees

1.  **Bit-Identical Reconstruction**: Reconstructing from `Snapshot(N) + Events(N+1..M)` must produce a `ReplayState` identical to applying `Events(0..M)` from scratch.
2.  **Temporal Consistency**: All events in a snapshot must maintain their original temporal ordering and `media_offset_ms`.
3.  **Media Offset Continuity**: `media_offset_ms` in the reconstructed state must remain continuous and monotonically increasing (if applicable).

## Cursor Anchoring Rules

1.  **Deterministic Indexing**: The `ReplayCursor` event index always refers to the 0-based position in the canonical event stream, regardless of whether a snapshot was used for reconstruction.
2.  **Anchor Alignment**: Snapshots should ideally be taken at "stable" boundaries, such as `NODE_ENTERED` or `CALL_COMPLETED`, although the system supports arbitrary offsets.

## Media Offset Guarantees

1.  **Authoritative Clocks**: The `media_offset_ms` captured during runtime is the authoritative time reference for the replay cursor.
2.  **Drift Protection**: Snapshot reconstruction must not introduce drift between the event timeline and the media timeline.

## Storage and Lifecycle

1.  **Pathing**: Snapshots are stored under `snapshots/YYYY-MM-DD/session_<id>/snapshot_<offset>.json`.
2.  **Discovery**: The `ReplayService` automatically discovers and uses the latest valid snapshot that is less than or equal to the requested seek offset.
