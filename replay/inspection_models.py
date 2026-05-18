from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Literal


ReferenceKind = Literal[
    "report_field",
    "session",
    "event",
    "snapshot",
    "media",
    "artifact",
    "timestamp",
]

AnomalySeverity = Literal["info", "warn", "error"]


@dataclass(frozen=True)
class Reference:
    """Tagged pointer into the report or a resolved replay artifact."""

    kind: ReferenceKind
    label: str
    field_path: str | None = None
    session_id: str | None = None
    event_id: str | None = None
    event_index: int | None = None
    media_time_ms: float | None = None
    t_ms: int | None = None
    snapshot_offset: int | None = None
    artifact_path: str | None = None
    value: str | int | float | None = None


@dataclass(frozen=True)
class Anomaly:
    """Operator-facing issue surfaced from replay state and artifact evidence."""

    code: str
    severity: AnomalySeverity
    explanation: str
    references: list[Reference] = field(default_factory=list)


@dataclass(frozen=True)
class NextStep:
    """Concrete operator action grounded to specific evidence in the report."""

    action: str
    rationale: str
    cites: list[Reference] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.cites:
            raise ValueError("NextStep.cites must be non-empty")


@dataclass(frozen=True)
class IdentitySection:
    """Canonical report identifiers for CLI headers, API consumers, and UI routing."""

    session_id: str | None = None
    call_sid: str | None = None
    source_kind: str | None = None
    source_path: str | None = None


@dataclass(frozen=True)
class ArtifactAvailabilityEntry:
    """Availability record for one replay artifact source resolved by the service layer."""

    artifact: str
    available: bool = False
    location: str | None = None
    detail: str | None = None
    file_count: int | None = None
    references: list[Reference] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactAvailabilitySection:
    """Resolved artifact inventory for operators deciding what evidence can be inspected next."""

    entries: list[ArtifactAvailabilityEntry] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SessionMetadataSection:
    """Session envelope metadata for transport adapters and analyst detail surfaces."""

    target: str | None = None
    started_at: float | None = None
    ended_at: float | None = None
    duration_ms: int | None = None
    manual_mode: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class SummarySection:
    """High-signal session summary used by CLI text views, API summaries, and UI overview cards."""

    event_count: int = 0
    prompt_count: int = 0
    action_count: int = 0
    node_count: int = 0
    first_prompt: str | None = None
    last_prompt: str | None = None
    last_action: str | None = None
    largest_gap_ms: int | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChronologyEntry:
    """Normalized timeline row for replay event inspection across transports."""

    seq: int
    kind: str
    t_ms: int
    delta_ms: int = 0
    text: str | None = None
    text_preview: str | None = None
    event_id: str | None = None
    node_id: str | None = None
    dtmf: str | None = None


@dataclass(frozen=True)
class ChronologySection:
    """Ordered replay chronology for timeline widgets, text rendering, and anomaly analysis."""

    entries: list[ChronologyEntry] = field(default_factory=list)


@dataclass(frozen=True)
class PathStep:
    """Prompt or action step within the traversed replay path."""

    event_index: int | None = None
    kind: str | None = None
    value: str | None = None
    t_ms: int | None = None
    node_id: str | None = None


@dataclass(frozen=True)
class PathSection:
    """Prompt/action traversal path for operator review and downstream comparison logic."""

    root_prompts: list[str] = field(default_factory=list)
    dtmf_path: list[str] = field(default_factory=list)
    unique_actions: list[str] = field(default_factory=list)
    visited_nodes: list[str] = field(default_factory=list)
    active_path: list[str] = field(default_factory=list)
    steps: list[PathStep] = field(default_factory=list)


@dataclass(frozen=True)
class StateDiagnosticsSection:
    """Replay-state and runtime diagnostic details consumed by debugging surfaces and tooling."""

    graph_node_count: int = 0
    transcript_count: int = 0
    visited_node_count: int = 0
    call_status: str | None = None
    snapshot_offset: int | None = None
    target_offset: int | None = None
    total_event_count: int | None = None
    queue: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class CorrelationSection:
    """Cross-artifact timing and alignment facts for operators and anomaly/next-step generation."""

    startup_to_gui_ready_ms: int | None = None
    session_start_to_first_prompt_ms: int | None = None
    session_start_to_first_action_ms: int | None = None
    stream_connect_to_first_prompt_ms: int | None = None
    session_duration_ms: int | None = None
    last_activity_at: float | None = None
    idle_for_s: float | None = None


@dataclass(frozen=True)
class BookmarkSummary:
    """Serializable bookmark projection using existing replay bookmark identifiers."""

    bookmark_id: str
    session_id: str
    event_id: str
    event_index: int
    media_time_ms: float
    label: str
    category: str
    note: str
    created_at: str | None = None
    source: str = "operator"


@dataclass(frozen=True)
class AnnotationSummary:
    """Serializable annotation projection using existing replay annotation identifiers."""

    annotation_id: str
    session_id: str
    event_id: str
    event_index: int
    media_time_ms: float
    type: str
    text: str
    severity: str
    created_at: str | None = None
    revision_of: str | None = None


@dataclass(frozen=True)
class BookmarksAnnotationsSection:
    """Operator-authored bookmarks and annotations for CLI, API, and analyst review surfaces."""

    bookmarks: list[BookmarkSummary] = field(default_factory=list)
    annotations: list[AnnotationSummary] = field(default_factory=list)


@dataclass(frozen=True)
class MediaStatusSection:
    """Recording and waveform status details for replay media tooling and operator playback."""

    recording_reference: str | None = None
    recording_path: str | None = None
    recording_available: bool = False
    waveform_reference: str | None = None
    waveform_path: str | None = None
    waveform_available: bool = False
    media_duration_ms: int | None = None
    replay_anchor_timestamp: str | None = None


@dataclass(frozen=True)
class ReplayInspectionReport:
    """Canonical replay inspection payload shared by CLI, API, UI, and the compat shim."""

    schema_version: str = "1.0"
    identity: IdentitySection = field(default_factory=IdentitySection)
    artifact_availability: ArtifactAvailabilitySection = field(
        default_factory=ArtifactAvailabilitySection
    )
    session_metadata: SessionMetadataSection = field(default_factory=SessionMetadataSection)
    summary: SummarySection = field(default_factory=SummarySection)
    chronology: ChronologySection = field(default_factory=ChronologySection)
    path: PathSection = field(default_factory=PathSection)
    state_diagnostics: StateDiagnosticsSection = field(default_factory=StateDiagnosticsSection)
    correlation: CorrelationSection = field(default_factory=CorrelationSection)
    anomalies: list[Anomaly] = field(default_factory=list)
    bookmarks_annotations: BookmarksAnnotationsSection = field(
        default_factory=BookmarksAnnotationsSection
    )
    media_status: MediaStatusSection = field(default_factory=MediaStatusSection)
    next_steps: list[NextStep] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "ReplayInspectionReport":
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2) + "\n"

    def write_json(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.write_text(self.to_json(), encoding="utf-8")
        return destination


__all__ = [
    "AnnotationSummary",
    "Anomaly",
    "AnomalySeverity",
    "ArtifactAvailabilityEntry",
    "ArtifactAvailabilitySection",
    "BookmarkSummary",
    "BookmarksAnnotationsSection",
    "ChronologyEntry",
    "ChronologySection",
    "CorrelationSection",
    "IdentitySection",
    "MediaStatusSection",
    "NextStep",
    "PathSection",
    "PathStep",
    "Reference",
    "ReferenceKind",
    "ReplayInspectionReport",
    "SessionMetadataSection",
    "StateDiagnosticsSection",
    "SummarySection",
]
