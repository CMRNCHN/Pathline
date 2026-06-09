"""runtime/storage.py — SQLite-backed persistence for the IVR Agent.

Single-user, personal-use storage. No ORM; pure sqlite3 with parameterized
queries and a row-factory that returns dicts. All datetimes stored as ISO 8601
strings and returned as timezone-aware datetime objects (UTC).

Public surface
--------------
StorageBackend   — the main class; construct with a path to the .db file.

Domain dataclasses defined here (persistence-layer representations)
--------------------------------------------------------------------
IVRSystem, IVRNode, IVREdge, PromptVariant, AnnouncedOption,
SessionObservation, GapTaskRecord, Session, Hypothesis
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Generator


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1

_DDL = """
-- ------------------------------------------------------------------ meta --
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL,
    applied_at  TEXT    NOT NULL   -- ISO 8601
);

-- ----------------------------------------------------------------- ivr systems --
CREATE TABLE IF NOT EXISTS ivr_systems (
    system_id       TEXT PRIMARY KEY,
    phone_number    TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL DEFAULT '',
    description     TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    metadata        TEXT NOT NULL DEFAULT '{}'   -- JSON blob
);
CREATE INDEX IF NOT EXISTS idx_ivr_systems_phone ON ivr_systems(phone_number);

-- ----------------------------------------------------------------- ivr nodes --
CREATE TABLE IF NOT EXISTS ivr_nodes (
    node_id         TEXT PRIMARY KEY,
    system_id       TEXT NOT NULL REFERENCES ivr_systems(system_id),
    canonical_key   TEXT NOT NULL,   -- normalized prompt key (for dedup)
    display_prompt  TEXT NOT NULL,   -- raw prompt text for display
    epistemic_state TEXT NOT NULL DEFAULT 'unknown',
    confidence      REAL NOT NULL DEFAULT 0.0,
    observation_count INTEGER NOT NULL DEFAULT 0,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ivr_nodes_system     ON ivr_nodes(system_id);
CREATE INDEX IF NOT EXISTS idx_ivr_nodes_canonical  ON ivr_nodes(system_id, canonical_key);
CREATE INDEX IF NOT EXISTS idx_ivr_nodes_confidence ON ivr_nodes(system_id, confidence);

-- ----------------------------------------------------------------- ivr edges --
CREATE TABLE IF NOT EXISTS ivr_edges (
    edge_id         TEXT PRIMARY KEY,
    system_id       TEXT NOT NULL REFERENCES ivr_systems(system_id),
    from_node_id    TEXT NOT NULL REFERENCES ivr_nodes(node_id),
    to_node_id      TEXT NOT NULL REFERENCES ivr_nodes(node_id),
    dtmf_option     TEXT NOT NULL,   -- e.g. "1", "2", "#", ""
    observation_count INTEGER NOT NULL DEFAULT 0,
    confidence      REAL NOT NULL DEFAULT 0.0,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ivr_edges_from   ON ivr_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_ivr_edges_to     ON ivr_edges(to_node_id);
CREATE INDEX IF NOT EXISTS idx_ivr_edges_system ON ivr_edges(system_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ivr_edges_unique ON ivr_edges(from_node_id, dtmf_option);

-- ----------------------------------------------------------------- prompt variants --
CREATE TABLE IF NOT EXISTS prompt_variants (
    variant_id  TEXT PRIMARY KEY,
    node_id     TEXT NOT NULL REFERENCES ivr_nodes(node_id),
    text        TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    seen_count  INTEGER NOT NULL DEFAULT 1,
    metadata    TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_prompt_variants_node ON prompt_variants(node_id);

-- ----------------------------------------------------------------- announced options --
CREATE TABLE IF NOT EXISTS announced_options (
    option_id   TEXT PRIMARY KEY,
    node_id     TEXT NOT NULL REFERENCES ivr_nodes(node_id),
    dtmf_digit  TEXT NOT NULL,
    label_text  TEXT NOT NULL DEFAULT '',
    first_seen_at TEXT NOT NULL,
    metadata    TEXT NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_announced_options_unique ON announced_options(node_id, dtmf_digit);
CREATE INDEX IF NOT EXISTS idx_announced_options_node ON announced_options(node_id);

-- ----------------------------------------------------------------- session observations --
-- Append-only; rows are NEVER updated or deleted after insert.
-- node_id is NULL for observations not yet linked to a known node.
CREATE TABLE IF NOT EXISTS session_observations (
    obs_id             TEXT PRIMARY KEY,
    session_id         TEXT NOT NULL,
    system_id          TEXT NOT NULL REFERENCES ivr_systems(system_id),
    node_id            TEXT             REFERENCES ivr_nodes(node_id),  -- nullable
    event_kind         TEXT NOT NULL,   -- "prompt" | "action" | "dtmf" | "hangup" | etc.
    event_text         TEXT NOT NULL DEFAULT '',
    t_ms               INTEGER NOT NULL DEFAULT 0,
    confidence         REAL    NOT NULL DEFAULT 1.0,
    observed_at        TEXT    NOT NULL,
    obs_schema_version TEXT    NOT NULL DEFAULT '1.0',  -- bump on field additions
    raw_payload        TEXT    NOT NULL DEFAULT '{}'    -- JSON: full original event
);
CREATE INDEX IF NOT EXISTS idx_obs_session  ON session_observations(session_id);
CREATE INDEX IF NOT EXISTS idx_obs_node     ON session_observations(node_id);
CREATE INDEX IF NOT EXISTS idx_obs_system   ON session_observations(system_id);
CREATE INDEX IF NOT EXISTS idx_obs_unlinked ON session_observations(system_id) WHERE node_id IS NULL;

-- ----------------------------------------------------------------- gap tasks --
CREATE TABLE IF NOT EXISTS gap_tasks (
    gap_id              TEXT PRIMARY KEY,
    system_id           TEXT NOT NULL REFERENCES ivr_systems(system_id),
    gap_type            TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    priority_score      REAL NOT NULL DEFAULT 0.0,
    operator_priority   REAL NOT NULL DEFAULT 0.5,
    target_node_id      TEXT             REFERENCES ivr_nodes(node_id),
    target_option       TEXT,
    planned_path        TEXT NOT NULL DEFAULT '[]',  -- JSON array of DTMF strings
    source_session_id   TEXT,
    source_engine       TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    in_progress_since   TEXT,
    resolved_at         TEXT,
    deferred_until      TEXT,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    max_retries         INTEGER NOT NULL DEFAULT 3,
    resolution_notes    TEXT,
    resolution_session_id TEXT,
    superseded_reason   TEXT,
    operator_context    TEXT,
    operator_label      TEXT,
    score_breakdown     TEXT NOT NULL DEFAULT '{}',  -- JSON
    extra_metadata      TEXT NOT NULL DEFAULT '{}'   -- JSON
);
CREATE INDEX IF NOT EXISTS idx_gaps_system_status   ON gap_tasks(system_id, status);
CREATE INDEX IF NOT EXISTS idx_gaps_priority        ON gap_tasks(system_id, priority_score DESC) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_gaps_deferred        ON gap_tasks(system_id, deferred_until) WHERE status = 'deferred';

-- ----------------------------------------------------------------- sessions --
CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    system_id       TEXT NOT NULL REFERENCES ivr_systems(system_id),
    gap_id          TEXT             REFERENCES gap_tasks(gap_id),
    status          TEXT NOT NULL DEFAULT 'active',  -- active | completed | failed
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    outcome         TEXT NOT NULL DEFAULT '{}'   -- JSON
);
CREATE INDEX IF NOT EXISTS idx_sessions_system ON sessions(system_id);
CREATE INDEX IF NOT EXISTS idx_sessions_gap    ON sessions(gap_id);

-- ----------------------------------------------------------------- hypotheses --
CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id   TEXT PRIMARY KEY,
    system_id       TEXT NOT NULL REFERENCES ivr_systems(system_id),
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | confirmed | refuted | abandoned
    confidence      REAL NOT NULL DEFAULT 0.5,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    evidence        TEXT NOT NULL DEFAULT '[]',  -- JSON array of obs_ids or notes
    metadata        TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_hypotheses_system ON hypotheses(system_id);
"""


# ---------------------------------------------------------------------------
# Domain dataclasses (persistence layer)
# ---------------------------------------------------------------------------

class EpistemicState(StrEnum):
    UNKNOWN      = "unknown"
    OBSERVED     = "observed"
    CONFIRMED    = "confirmed"
    DRIFTED      = "drifted"
    DEPRECATED   = "deprecated"


@dataclass
class IVRSystem:
    system_id:    str
    phone_number: str
    display_name: str = ""
    description:  str = ""
    created_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata:     dict[str, Any] = field(default_factory=dict)


@dataclass
class IVRNode:
    node_id:           str
    system_id:         str
    canonical_key:     str
    display_prompt:    str
    epistemic_state:   EpistemicState = EpistemicState.UNKNOWN
    confidence:        float = 0.0
    observation_count: int = 0
    first_seen_at:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata:          dict[str, Any] = field(default_factory=dict)


@dataclass
class IVREdge:
    edge_id:           str
    system_id:         str
    from_node_id:      str
    to_node_id:        str
    dtmf_option:       str
    observation_count: int = 0
    confidence:        float = 0.0
    first_seen_at:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata:          dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptVariant:
    variant_id:   str
    node_id:      str
    text:         str
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    seen_count:   int = 1
    metadata:     dict[str, Any] = field(default_factory=dict)


@dataclass
class AnnouncedOption:
    option_id:    str
    node_id:      str
    dtmf_digit:   str
    label_text:   str = ""
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata:     dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionObservation:
    obs_id:             str
    session_id:         str
    system_id:          str
    event_kind:         str
    event_text:         str = ""
    t_ms:               int = 0
    confidence:         float = 1.0
    observed_at:        datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    node_id:            str | None = None
    obs_schema_version: str = "1.0"
    raw_payload:        dict[str, Any] = field(default_factory=dict)


@dataclass
class GapTaskRecord:
    """Persistence-layer representation of a GapTask.

    Mirrors runtime.gap_task.GapTask but uses plain Python types that map
    cleanly to SQLite columns. JSON blobs handle nested structures.
    """
    gap_id:             str
    system_id:          str
    gap_type:           str
    status:             str = "pending"
    priority_score:     float = 0.0
    operator_priority:  float = 0.5
    target_node_id:     str | None = None
    target_option:      str | None = None
    planned_path:       list[str] = field(default_factory=list)
    source_session_id:  str | None = None
    source_engine:      str | None = None
    created_at:         datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:         datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    in_progress_since:  datetime | None = None
    resolved_at:        datetime | None = None
    deferred_until:     datetime | None = None
    retry_count:        int = 0
    max_retries:        int = 3
    resolution_notes:   str | None = None
    resolution_session_id: str | None = None
    superseded_reason:  str | None = None
    operator_context:   str | None = None
    operator_label:     str | None = None
    score_breakdown:    dict[str, Any] = field(default_factory=dict)
    extra_metadata:     dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    session_id: str
    system_id:  str
    gap_id:     str | None = None
    status:     str = "active"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at:   datetime | None = None
    outcome:    dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypothesis:
    hypothesis_id: str
    system_id:     str
    description:   str = ""
    status:        str = "pending"
    confidence:    float = 0.5
    created_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence:      list[str] = field(default_factory=list)
    metadata:      dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    """Serialize a datetime to an ISO 8601 string (UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _dt(s: str | None) -> datetime | None:
    """Deserialize an ISO 8601 string to a timezone-aware UTC datetime."""
    if s is None:
        return None
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dt_req(s: str) -> datetime:
    """Like _dt but raises if s is None (for non-nullable columns)."""
    result = _dt(s)
    if result is None:
        raise ValueError("Expected non-null datetime string")
    return result


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, default=str)


def _json_loads(s: str | None) -> Any:
    if not s:
        return {}
    return json.loads(s)


def _row_to_ivr_system(row: dict) -> IVRSystem:
    return IVRSystem(
        system_id=row["system_id"],
        phone_number=row["phone_number"],
        display_name=row["display_name"],
        description=row["description"],
        created_at=_dt_req(row["created_at"]),
        updated_at=_dt_req(row["updated_at"]),
        metadata=_json_loads(row["metadata"]),
    )


def _row_to_ivr_node(row: dict) -> IVRNode:
    return IVRNode(
        node_id=row["node_id"],
        system_id=row["system_id"],
        canonical_key=row["canonical_key"],
        display_prompt=row["display_prompt"],
        epistemic_state=EpistemicState(row["epistemic_state"]),
        confidence=row["confidence"],
        observation_count=row["observation_count"],
        first_seen_at=_dt_req(row["first_seen_at"]),
        last_seen_at=_dt_req(row["last_seen_at"]),
        metadata=_json_loads(row["metadata"]),
    )


def _row_to_observation(row: dict) -> SessionObservation:
    return SessionObservation(
        obs_id=row["obs_id"],
        session_id=row["session_id"],
        system_id=row["system_id"],
        node_id=row["node_id"],
        event_kind=row["event_kind"],
        event_text=row["event_text"],
        t_ms=row["t_ms"],
        confidence=row["confidence"],
        observed_at=_dt_req(row["observed_at"]),
        raw_payload=_json_loads(row["raw_payload"]),
    )


def _row_to_gap_task(row: dict) -> GapTaskRecord:
    return GapTaskRecord(
        gap_id=row["gap_id"],
        system_id=row["system_id"],
        gap_type=row["gap_type"],
        status=row["status"],
        priority_score=row["priority_score"],
        operator_priority=row["operator_priority"],
        target_node_id=row["target_node_id"],
        target_option=row["target_option"],
        planned_path=json.loads(row["planned_path"]),
        source_session_id=row["source_session_id"],
        source_engine=row["source_engine"],
        created_at=_dt_req(row["created_at"]),
        updated_at=_dt_req(row["updated_at"]),
        in_progress_since=_dt(row["in_progress_since"]),
        resolved_at=_dt(row["resolved_at"]),
        deferred_until=_dt(row["deferred_until"]),
        retry_count=row["retry_count"],
        max_retries=row["max_retries"],
        resolution_notes=row["resolution_notes"],
        resolution_session_id=row["resolution_session_id"],
        superseded_reason=row["superseded_reason"],
        operator_context=row["operator_context"],
        operator_label=row["operator_label"],
        score_breakdown=_json_loads(row["score_breakdown"]),
        extra_metadata=_json_loads(row["extra_metadata"]),
    )


def _row_to_session(row: dict) -> Session:
    return Session(
        session_id=row["session_id"],
        system_id=row["system_id"],
        gap_id=row["gap_id"],
        status=row["status"],
        started_at=_dt_req(row["started_at"]),
        ended_at=_dt(row["ended_at"]),
        outcome=_json_loads(row["outcome"]),
    )


# ---------------------------------------------------------------------------
# StorageBackend
# ---------------------------------------------------------------------------

class StorageBackend:
    """SQLite-backed persistence for the IVR agent.

    Usage::

        db = StorageBackend(Path("data/ivr_agent.db"))
        system = IVRSystem(system_id=str(uuid4()), phone_number="+18005551234")
        db.upsert_ivr_system(system)

    All public methods acquire a short-lived connection via _connect().
    The WAL journal mode is enabled for better concurrent read performance
    (multiple readers + one writer is the expected workload pattern).
    """

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _row_dict(self, row: sqlite3.Row) -> dict:
        return dict(row)

    # ------------------------------------------------------------------
    # Initialization / migrations
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)
            row = conn.execute(
                "SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, _iso(datetime.now(timezone.utc))),
                )

    def schema_version(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            return row["version"] if row else 0

    # ------------------------------------------------------------------
    # IVR System CRUD
    # ------------------------------------------------------------------

    def upsert_ivr_system(self, system: IVRSystem) -> str:
        """Insert or replace an IVRSystem. Returns system_id."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ivr_systems
                    (system_id, phone_number, display_name, description,
                     created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(system_id) DO UPDATE SET
                    phone_number = excluded.phone_number,
                    display_name = excluded.display_name,
                    description  = excluded.description,
                    updated_at   = excluded.updated_at,
                    metadata     = excluded.metadata
                """,
                (
                    system.system_id,
                    system.phone_number,
                    system.display_name,
                    system.description,
                    _iso(system.created_at),
                    _iso(system.updated_at),
                    _json_dumps(system.metadata),
                ),
            )
        return system.system_id

    def get_ivr_system(self, system_id: str) -> IVRSystem | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ivr_systems WHERE system_id = ?", (system_id,)
            ).fetchone()
        if row is None:
            return None
        return _row_to_ivr_system(self._row_dict(row))

    def list_ivr_systems(self) -> list[IVRSystem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ivr_systems ORDER BY display_name, phone_number"
            ).fetchall()
        return [_row_to_ivr_system(self._row_dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def upsert_node(self, node: IVRNode) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ivr_nodes
                    (node_id, system_id, canonical_key, display_prompt,
                     epistemic_state, confidence, observation_count,
                     first_seen_at, last_seen_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    canonical_key     = excluded.canonical_key,
                    display_prompt    = excluded.display_prompt,
                    epistemic_state   = excluded.epistemic_state,
                    confidence        = excluded.confidence,
                    observation_count = excluded.observation_count,
                    last_seen_at      = excluded.last_seen_at,
                    metadata          = excluded.metadata
                """,
                (
                    node.node_id,
                    node.system_id,
                    node.canonical_key,
                    node.display_prompt,
                    str(node.epistemic_state),
                    node.confidence,
                    node.observation_count,
                    _iso(node.first_seen_at),
                    _iso(node.last_seen_at),
                    _json_dumps(node.metadata),
                ),
            )

    def get_node(self, node_id: str) -> IVRNode | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ivr_nodes WHERE node_id = ?", (node_id,)
            ).fetchone()
        if row is None:
            return None
        return _row_to_ivr_node(self._row_dict(row))

    def get_nodes_by_system(self, system_id: str) -> list[IVRNode]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ivr_nodes WHERE system_id = ? ORDER BY last_seen_at DESC",
                (system_id,),
            ).fetchall()
        return [_row_to_ivr_node(self._row_dict(r)) for r in rows]

    def get_nodes_below_confidence(
        self, system_id: str, threshold: float, now: datetime
    ) -> list[IVRNode]:
        """Return nodes whose confidence is below threshold.

        The ``now`` parameter is accepted for API consistency with callers
        that may want to implement time-weighted decay; it is not used in
        the current query but is available for future WHERE-clause extensions.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ivr_nodes
                WHERE system_id = ?
                  AND confidence < ?
                  AND epistemic_state NOT IN ('deprecated')
                ORDER BY confidence ASC
                """,
                (system_id, threshold),
            ).fetchall()
        return [_row_to_ivr_node(self._row_dict(r)) for r in rows]

    def update_epistemic_state(
        self, node_id: str, new_state: EpistemicState, now: datetime
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ivr_nodes
                SET epistemic_state = ?, last_seen_at = ?
                WHERE node_id = ?
                """,
                (str(new_state), _iso(now), node_id),
            )

    # ------------------------------------------------------------------
    # Observation log (append-only, immutable)
    # ------------------------------------------------------------------

    def append_observation(self, obs: SessionObservation) -> None:
        """Insert an observation. Never call UPDATE or DELETE on this table."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO session_observations
                    (obs_id, session_id, system_id, node_id, event_kind,
                     event_text, t_ms, confidence, observed_at,
                     obs_schema_version, raw_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obs.obs_id,
                    obs.session_id,
                    obs.system_id,
                    obs.node_id,
                    obs.event_kind,
                    obs.event_text,
                    obs.t_ms,
                    obs.confidence,
                    _iso(obs.observed_at),
                    obs.obs_schema_version,
                    _json_dumps(obs.raw_payload),
                ),
            )

    def get_observations_for_session(self, session_id: str) -> list[SessionObservation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM session_observations
                WHERE session_id = ?
                ORDER BY t_ms ASC, rowid ASC
                """,
                (session_id,),
            ).fetchall()
        return [_row_to_observation(self._row_dict(r)) for r in rows]

    def get_observations_for_node(self, node_id: str) -> list[SessionObservation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM session_observations
                WHERE node_id = ?
                ORDER BY observed_at ASC
                """,
                (node_id,),
            ).fetchall()
        return [_row_to_observation(self._row_dict(r)) for r in rows]

    def get_unlinked_observations(self, system_id: str) -> list[SessionObservation]:
        """Return observations that have not yet been linked to a node (node_id IS NULL)."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM session_observations
                WHERE system_id = ?
                  AND node_id IS NULL
                ORDER BY observed_at ASC
                """,
                (system_id,),
            ).fetchall()
        return [_row_to_observation(self._row_dict(r)) for r in rows]

    def link_observation_to_node(self, obs_id: str, node_id: str) -> None:
        """Lazy-link an observation to a node once the node has been identified.

        This is the one permitted UPDATE on session_observations — it fills in
        the foreign key that was NULL at insert time. The event data itself
        (event_kind, event_text, raw_payload, observed_at) is never mutated.
        """
        with self._connect() as conn:
            conn.execute(
                "UPDATE session_observations SET node_id = ? WHERE obs_id = ?",
                (node_id, obs_id),
            )

    # ------------------------------------------------------------------
    # Gap task queue
    # ------------------------------------------------------------------

    def push_gap(self, task: GapTaskRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO gap_tasks
                    (gap_id, system_id, gap_type, status, priority_score,
                     operator_priority, target_node_id, target_option,
                     planned_path, source_session_id, source_engine,
                     created_at, updated_at, in_progress_since, resolved_at,
                     deferred_until, retry_count, max_retries, resolution_notes,
                     resolution_session_id, superseded_reason, operator_context,
                     operator_label, score_breakdown, extra_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.gap_id,
                    task.system_id,
                    task.gap_type,
                    task.status,
                    task.priority_score,
                    task.operator_priority,
                    task.target_node_id,
                    task.target_option,
                    _json_dumps(task.planned_path),
                    task.source_session_id,
                    task.source_engine,
                    _iso(task.created_at),
                    _iso(task.updated_at),
                    _iso(task.in_progress_since) if task.in_progress_since else None,
                    _iso(task.resolved_at) if task.resolved_at else None,
                    _iso(task.deferred_until) if task.deferred_until else None,
                    task.retry_count,
                    task.max_retries,
                    task.resolution_notes,
                    task.resolution_session_id,
                    task.superseded_reason,
                    task.operator_context,
                    task.operator_label,
                    _json_dumps(task.score_breakdown),
                    _json_dumps(task.extra_metadata),
                ),
            )

    def pop_highest_priority(
        self, system_id: str, now: datetime
    ) -> GapTaskRecord | None:
        """Atomically claim the highest-priority PENDING gap and mark it IN_PROGRESS.

        Also re-activates any DEFERRED gaps whose deferred_until has elapsed
        before selecting the top candidate.
        """
        with self._connect() as conn:
            # Re-activate deferred gaps whose time has come.
            conn.execute(
                """
                UPDATE gap_tasks
                SET status = 'pending', updated_at = ?
                WHERE system_id = ?
                  AND status = 'deferred'
                  AND deferred_until IS NOT NULL
                  AND deferred_until <= ?
                """,
                (_iso(now), system_id, _iso(now)),
            )
            row = conn.execute(
                """
                SELECT * FROM gap_tasks
                WHERE system_id = ?
                  AND status = 'pending'
                ORDER BY priority_score DESC
                LIMIT 1
                """,
                (system_id,),
            ).fetchone()
            if row is None:
                return None
            gap_id = row["gap_id"]
            conn.execute(
                """
                UPDATE gap_tasks
                SET status = 'in_progress',
                    in_progress_since = ?,
                    updated_at = ?
                WHERE gap_id = ?
                """,
                (_iso(now), _iso(now), gap_id),
            )
            updated = conn.execute(
                "SELECT * FROM gap_tasks WHERE gap_id = ?", (gap_id,)
            ).fetchone()
        return _row_to_gap_task(self._row_dict(updated))

    def get_pending_gaps(self, system_id: str) -> list[GapTaskRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM gap_tasks
                WHERE system_id = ? AND status = 'pending'
                ORDER BY priority_score DESC
                """,
                (system_id,),
            ).fetchall()
        return [_row_to_gap_task(self._row_dict(r)) for r in rows]

    def update_gap(self, task) -> None:
        """Update priority_score and updated_at on an existing gap. No-op if not found."""
        gap_id = getattr(task, 'gap_id', None)
        if not gap_id:
            return
        ps = task.priority_score() if callable(getattr(task, 'priority_score', None)) else float(getattr(task, 'priority_score', 0.0))
        with self._connect() as conn:
            conn.execute(
                "UPDATE gap_tasks SET priority_score = ?, updated_at = ? WHERE gap_id = ?",
                (ps, _iso(datetime.now(timezone.utc)), gap_id),
            )

    def save_gap(self, task) -> None:
        """Accept either GapTaskRecord or GapTask (from runtime.gap_task) and persist."""
        if isinstance(task, GapTaskRecord):
            self.push_gap(task)
            return
        # Convert runtime.gap_task.GapTask → GapTaskRecord
        record = GapTaskRecord(
            gap_id=task.gap_id,
            system_id=task.target_ivr_id,
            gap_type=str(task.gap_type),
            status=str(task.status),
            priority_score=task.priority_score() if callable(getattr(task, 'priority_score', None)) else float(task.priority_score),
            operator_priority=float(task.operator_priority),
            target_node_id=task.target_node_key,
            target_option=task.target_option,
            planned_path=list(task.planned_path or []),
            source_session_id=task.source_session_id,
            source_engine=task.source_engine,
            created_at=task.created_at,
            updated_at=task.updated_at,
            in_progress_since=task.in_progress_since,
            resolved_at=task.resolved_at,
            deferred_until=task.deferred_until,
            retry_count=int(task.retry_count),
            max_retries=int(task.max_retries),
            resolution_notes=task.resolution_notes,
            resolution_session_id=task.resolution_session_id,
            superseded_reason=task.superseded_reason,
            operator_context=task.operator_context,
            operator_label=task.operator_label,
            score_breakdown=task.score_breakdown.__dict__ if hasattr(task.score_breakdown, '__dict__') else (dict(task.score_breakdown) if task.score_breakdown else {}),
        )
        self.push_gap(record)

    def load_existing_gaps(
        self,
        system_id: str,
        statuses: list[str] | None = None,
    ) -> list[GapTaskRecord]:
        """Return gaps for *system_id* filtered by status list (default: pending + in_progress)."""
        if statuses is None:
            statuses = ["pending", "in_progress"]
        placeholders = ",".join("?" * len(statuses))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM gap_tasks WHERE system_id = ? AND status IN ({placeholders}) "
                f"ORDER BY priority_score DESC",
                [system_id, *statuses],
            ).fetchall()
        return [_row_to_gap_task(self._row_dict(r)) for r in rows]

    def mark_gap_resolved(self, gap_id: str, resolution_note: str) -> None:
        now = _iso(datetime.now(timezone.utc))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE gap_tasks
                SET status = 'resolved',
                    resolved_at = ?,
                    updated_at  = ?,
                    resolution_notes = ?
                WHERE gap_id = ?
                """,
                (now, now, resolution_note, gap_id),
            )

    def mark_gap_in_progress(self, gap_id: str) -> None:
        now = _iso(datetime.now(timezone.utc))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE gap_tasks
                SET status = 'in_progress',
                    in_progress_since = ?,
                    updated_at = ?
                WHERE gap_id = ?
                """,
                (now, now, gap_id),
            )

    def rescore_all(self, system_id: str, now: datetime) -> None:
        """Recompute priority_score for all PENDING gaps in the given system.

        The scoring formula mirrors PriorityScoreBreakdown.final_score:
            score = 0.35 * impact + 0.25 * urgency + 0.20 * confidence_benefit
                  + 0.15 * operator_priority + 0.05 * freshness_bonus

        Since impact and confidence_benefit require graph context not available
        inside the storage layer, those components are read from the
        score_breakdown JSON blob stored with each gap. The components that
        CAN be recomputed purely from stored fields are:

        - urgency:        min(1.0, days_since_created / 30)
        - freshness_bonus: max(0.0, 1.0 - hours_since_created / 24)

        The other three components (impact_score, confidence_benefit,
        user_priority / operator_priority) are read from the existing
        score_breakdown JSON and NOT changed here — callers that want to
        update those must call push_gap() or a dedicated update method.

        This method intentionally only handles the time-dependent recalculation
        that can be done in-place without external graph data.
        """
        now_iso = _iso(now)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT gap_id, created_at, operator_priority, score_breakdown
                FROM gap_tasks
                WHERE system_id = ? AND status = 'pending'
                """,
                (system_id,),
            ).fetchall()

            for row in rows:
                created = _dt_req(row["created_at"])
                elapsed_days = (now - created).total_seconds() / 86400.0
                elapsed_hours = elapsed_days * 24.0

                urgency = min(1.0, elapsed_days / 30.0)
                freshness = max(0.0, 1.0 - elapsed_hours / 24.0)

                breakdown = _json_loads(row["score_breakdown"])
                impact = float(breakdown.get("impact_score", 0.05))
                conf_benefit = float(breakdown.get("confidence_benefit", 0.5))
                op_priority = float(row["operator_priority"])

                score = (
                    0.35 * impact
                    + 0.25 * urgency
                    + 0.20 * conf_benefit
                    + 0.15 * op_priority
                    + 0.05 * freshness
                )

                breakdown["urgency_score"] = urgency
                breakdown["freshness_bonus"] = freshness

                conn.execute(
                    """
                    UPDATE gap_tasks
                    SET priority_score  = ?,
                        score_breakdown = ?,
                        updated_at      = ?
                    WHERE gap_id = ?
                    """,
                    (_round(score), _json_dumps(breakdown), now_iso, row["gap_id"]),
                )

    # ------------------------------------------------------------------
    # Session recording
    # ------------------------------------------------------------------

    def start_session(self, session: Session) -> str:
        """Persist a new session record. Returns session_id."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (session_id, system_id, gap_id, status, started_at, ended_at, outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.system_id,
                    session.gap_id,
                    session.status,
                    _iso(session.started_at),
                    _iso(session.ended_at) if session.ended_at else None,
                    _json_dumps(session.outcome),
                ),
            )
        return session.session_id

    def end_session(self, session_id: str, outcome: dict) -> None:
        now = _iso(datetime.now(timezone.utc))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET status   = 'completed',
                    ended_at = ?,
                    outcome  = ?
                WHERE session_id = ?
                """,
                (now, _json_dumps(outcome), session_id),
            )

    def get_session(self, session_id: str) -> Session | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        return _row_to_session(self._row_dict(row))

    # ------------------------------------------------------------------
    # Edge operations (bonus — referenced by schema)
    # ------------------------------------------------------------------

    def upsert_edge(self, edge: IVREdge) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ivr_edges
                    (edge_id, system_id, from_node_id, to_node_id, dtmf_option,
                     observation_count, confidence, first_seen_at, last_seen_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(from_node_id, dtmf_option) DO UPDATE SET
                    to_node_id        = excluded.to_node_id,
                    observation_count = excluded.observation_count,
                    confidence        = excluded.confidence,
                    last_seen_at      = excluded.last_seen_at,
                    metadata          = excluded.metadata
                """,
                (
                    edge.edge_id,
                    edge.system_id,
                    edge.from_node_id,
                    edge.to_node_id,
                    edge.dtmf_option,
                    edge.observation_count,
                    edge.confidence,
                    _iso(edge.first_seen_at),
                    _iso(edge.last_seen_at),
                    _json_dumps(edge.metadata),
                ),
            )

    def get_edges_from_node(self, from_node_id: str) -> list[IVREdge]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ivr_edges WHERE from_node_id = ? ORDER BY dtmf_option",
                (from_node_id,),
            ).fetchall()
        return [_row_to_edge(self._row_dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Announced options
    # ------------------------------------------------------------------

    def upsert_announced_option(self, opt: AnnouncedOption) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO announced_options
                    (option_id, node_id, dtmf_digit, label_text, first_seen_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id, dtmf_digit) DO UPDATE SET
                    label_text = excluded.label_text,
                    metadata   = excluded.metadata
                """,
                (
                    opt.option_id,
                    opt.node_id,
                    opt.dtmf_digit,
                    opt.label_text,
                    _iso(opt.first_seen_at),
                    _json_dumps(opt.metadata),
                ),
            )

    def get_announced_options(self, node_id: str) -> list[AnnouncedOption]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM announced_options WHERE node_id = ? ORDER BY dtmf_digit",
                (node_id,),
            ).fetchall()
        return [_row_to_announced_option(self._row_dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Prompt variants
    # ------------------------------------------------------------------

    def upsert_prompt_variant(self, variant: PromptVariant) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO prompt_variants
                    (variant_id, node_id, text, first_seen_at, last_seen_at, seen_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(variant_id) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    seen_count   = seen_count + 1,
                    metadata     = excluded.metadata
                """,
                (
                    variant.variant_id,
                    variant.node_id,
                    variant.text,
                    _iso(variant.first_seen_at),
                    _iso(variant.last_seen_at),
                    variant.seen_count,
                    _json_dumps(variant.metadata),
                ),
            )

    # ------------------------------------------------------------------
    # Hypotheses
    # ------------------------------------------------------------------

    def upsert_hypothesis(self, h: Hypothesis) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hypotheses
                    (hypothesis_id, system_id, description, status, confidence,
                     created_at, updated_at, evidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hypothesis_id) DO UPDATE SET
                    description = excluded.description,
                    status      = excluded.status,
                    confidence  = excluded.confidence,
                    updated_at  = excluded.updated_at,
                    evidence    = excluded.evidence,
                    metadata    = excluded.metadata
                """,
                (
                    h.hypothesis_id,
                    h.system_id,
                    h.description,
                    h.status,
                    h.confidence,
                    _iso(h.created_at),
                    _iso(h.updated_at),
                    _json_dumps(h.evidence),
                    _json_dumps(h.metadata),
                ),
            )

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM hypotheses WHERE hypothesis_id = ?", (hypothesis_id,)
            ).fetchone()
        if row is None:
            return None
        return _row_to_hypothesis(self._row_dict(row))

    def list_hypotheses(self, system_id: str) -> list[Hypothesis]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hypotheses WHERE system_id = ? ORDER BY created_at DESC",
                (system_id,),
            ).fetchall()
        return [_row_to_hypothesis(self._row_dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Private helpers for remaining row-to-dataclass conversions
# ---------------------------------------------------------------------------

def _row_to_edge(row: dict) -> IVREdge:
    return IVREdge(
        edge_id=row["edge_id"],
        system_id=row["system_id"],
        from_node_id=row["from_node_id"],
        to_node_id=row["to_node_id"],
        dtmf_option=row["dtmf_option"],
        observation_count=row["observation_count"],
        confidence=row["confidence"],
        first_seen_at=_dt_req(row["first_seen_at"]),
        last_seen_at=_dt_req(row["last_seen_at"]),
        metadata=_json_loads(row["metadata"]),
    )


def _row_to_announced_option(row: dict) -> AnnouncedOption:
    return AnnouncedOption(
        option_id=row["option_id"],
        node_id=row["node_id"],
        dtmf_digit=row["dtmf_digit"],
        label_text=row["label_text"],
        first_seen_at=_dt_req(row["first_seen_at"]),
        metadata=_json_loads(row["metadata"]),
    )


def _row_to_hypothesis(row: dict) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=row["hypothesis_id"],
        system_id=row["system_id"],
        description=row["description"],
        status=row["status"],
        confidence=row["confidence"],
        created_at=_dt_req(row["created_at"]),
        updated_at=_dt_req(row["updated_at"]),
        evidence=json.loads(row["evidence"]),
        metadata=_json_loads(row["metadata"]),
    )


def _round(v: float, ndigits: int = 6) -> float:
    return round(v, ndigits)
