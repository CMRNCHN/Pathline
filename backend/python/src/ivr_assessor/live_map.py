from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import time
from typing import Protocol

from .events.event_bus import bus as EventBus
from .events.event_types import EventType
from .events.event_models import OperationalEvent, EventMetadata

from .event_ledger import EventLedger
from .exploration import choose_candidate
from .ivr_mapper import IvrMapper
from .models import CallEvent
from .prompt_intelligence import classify_prompt
from .response_library import ResponseClip, ResponseLibrary
from .scenario_runner import NextActionKind, choose_next_action
from .telephony import TelephonyClient


class PromptSource(Protocol):
    def next_event(self, session_id: str) -> CallEvent | None: ...


@dataclass
class ScriptedPromptSource:
    prompts: list[CallEvent]
    _index: int = 0

    def next_event(self, session_id: str) -> CallEvent | None:  # noqa: ARG002
        if self._index >= len(self.prompts):
            return None

        event = self.prompts[self._index]
        self._index += 1
        return event


@dataclass
class InteractivePromptSource:
    """A prompt source that gets prompts from the user via the command line."""

    _t_start: float = field(default_factory=time.time)

    def next_event(self, session_id: str) -> CallEvent | None:  # noqa: ARG002
        try:
            prompt_text = input("Enter prompt text (or press Ctrl+D to end): ")
            t_now = time.time()
            t_ms = int((t_now - self._t_start) * 1000)
            return CallEvent(kind="prompt", text=prompt_text, t_ms=t_ms)
        except EOFError:
            return None


@dataclass
class RecordingTelephonyClient:
    """Simulated telephony backend used for scripted/offline mapping runs."""

    dialed: list[tuple[str, str]] = field(default_factory=list)
    dtmf_sent: list[tuple[str, str]] = field(default_factory=list)
    clips_played: list[tuple[str, str]] = field(default_factory=list)
    said: list[tuple[str, str]] = field(default_factory=list)
    hung_up: list[str] = field(default_factory=list)

    def dial(self, target_number: str) -> str:
        session_id = f"session-{len(self.dialed) + 1}"
        self.dialed.append((target_number, session_id))
        return session_id

    def send_dtmf(self, session_id: str, digits: str) -> None:
        self.dtmf_sent.append((session_id, digits))

    def play_clip(self, session_id: str, file_path: str) -> None:
        self.clips_played.append((session_id, file_path))

    def say(self, session_id: str, text: str) -> None:
        self.said.append((session_id, text))

    def hangup(self, session_id: str) -> None:
        self.hung_up.append(session_id)


def build_default_response_library(
    label: str,
    response_style: str | None = None,
) -> ResponseLibrary:
    """Returns a ResponseLibrary with a single default clip for the given label."""
    style = response_style or "default"
    clip_id = f"{label}-{style}" if response_style else label
    return ResponseLibrary(
        clips=[
            ResponseClip(
                id=clip_id,
                label=label,
                file_path=Path(f"responses/{label}.wav"),
                style=style,
                duration_ms=2000,
            )
        ]
    )


@dataclass(frozen=True)
class LiveMappingSummary:
    target_number: str
    session_id: str
    response_mode: str
    events: list[dict[str, object]]
    graph: dict[str, dict[str, object]]
    last_action: str | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class LiveMappingSession:
    target_number: str
    response_mode: str
    prompt_source: PromptSource
    telephony: TelephonyClient
    response_library: ResponseLibrary
    response_label: str = "general"
    response_style: str | None = None
    session_id: str | None = None
    exploration_budget: int = 1
    confidence_threshold: float = 0.7
    mapper: IvrMapper = field(default_factory=IvrMapper)
    ledger: EventLedger = field(default_factory=EventLedger)
    max_actions: int = 20
    manual_mode: bool = False  # When True, observe prompts but don't take auto actions
    # Wall-clock soft cap (seconds). When the elapsed run time exceeds this,
    # we stop pulling NEW prompts but still finish processing the current one
    # — that "finish the current prompt" semantic is what keeps us from
    # losing the last transcription on the way out.
    wall_clock_cap_s: float | None = None
    # Pre-computed DTMF path the iterative-discovery loop wants this session
    # to walk first (e.g. ["1", "3"] meaning "press 1, then 3"). When set,
    # the session prefers these digits at successive menu prompts before
    # falling back to the normal exploration heuristic. Out of digits → fall
    # back to choose_candidate() as before.
    forced_branches: list[str] = field(default_factory=list)
    _clock: object = field(default=None, repr=False)

    def run(self) -> LiveMappingSummary:
        from .runtime.runtime_supervisor import supervisor
        session_id = self.session_id or self.telephony.dial(self.target_number)
        self.session_id = session_id
        last_action: str | None = None
        action_count = 0

        clock = self._clock if callable(self._clock) else time.time
        started = clock()
        forced = list(self.forced_branches)

        def _over_cap() -> bool:
            return self.wall_clock_cap_s is not None and (clock() - started) >= self.wall_clock_cap_s

        while action_count < self.max_actions:
            # Emit heartbeat for supervisor
            supervisor.record_heartbeat(session_id)

            if _over_cap():
                break
            event = self.prompt_source.next_event(session_id)
            if event is None:
                break

            self._record_event(event, branch_confidence=self._prompt_confidence(event))

            if event.kind != "prompt":
                continue

            # Manual mode: still observe & record, but skip automatic action selection.
            if self.manual_mode:
                continue

            classification = classify_prompt(event.text)
            next_action = choose_next_action(
                classification=classification,
                exploration_budget=self.exploration_budget,
                confidence_threshold=self.confidence_threshold,
            )

            if next_action.kind == NextActionKind.SEND_DTMF and next_action.payload is not None:
                # If the discovery loop pre-planned a path, prefer the next
                # digit on that path when it's actually announced by this
                # menu — otherwise fall back to least-explored.
                options = classification.options or [next_action.payload]
                forced_digit: str | None = None
                if forced and forced[0] in options:
                    forced_digit = forced.pop(0)
                if forced_digit is not None:
                    digits = forced_digit
                else:
                    candidate = choose_candidate(
                        graph=self.mapper.graph(),
                        observed_prompt=event.text,
                        available_options=options,
                        exploration_budget=self.exploration_budget,
                    )
                    if candidate.kind == "end_call":
                        break
                    digits = candidate.payload or next_action.payload
                self.telephony.send_dtmf(session_id, digits)
                action_event = CallEvent(
                    kind="action",
                    text=f"dtmf:{digits}",
                    t_ms=event.t_ms + 100,
                )
                self._record_event(action_event, branch_confidence=1.0)
                last_action = action_event.text
                action_count += 1
            elif next_action.kind == NextActionKind.PLAY_CLIP and next_action.payload is not None:
                try:
                    clip = self.response_library.pick(label=next_action.payload)
                    self.telephony.play_clip(session_id, str(clip.file_path))
                    action_event = CallEvent(
                        kind="action",
                        text=f"play:{clip.id}",
                        t_ms=event.t_ms + 100,
                    )
                    self._record_event(action_event, branch_confidence=1.0)
                    last_action = action_event.text
                    action_count += 1
                except LookupError:
                    # If a required clip is missing, we cannot proceed down this path.
                    break
            elif next_action.kind == NextActionKind.WAIT and self.response_mode == "voice":
                # In voice mode, play the general response clip as a fallback.
                try:
                    clip = self.response_library.pick(
                        label=self.response_label, style=self.response_style
                    )
                    self.telephony.play_clip(session_id, str(clip.file_path))
                    action_event = CallEvent(
                        kind="action",
                        text=f"play:{clip.id}",
                        t_ms=event.t_ms + 100,
                    )
                    self._record_event(action_event, branch_confidence=1.0)
                    last_action = action_event.text
                    action_count += 1
                except LookupError:
                    break

        self.telephony.hangup(session_id)
        EventBus.publish(OperationalEvent(
            type=EventType.CALL_ENDED,
            payload={"session_id": session_id},
            meta=EventMetadata(session_id=session_id, source_component="live_map")
        ))
        return LiveMappingSummary(
            target_number=self.target_number,
            session_id=session_id,
            response_mode=self.response_mode,
            events=[asdict(event) for event in self.ledger.all()],
            graph=self.mapper.graph(),
            last_action=last_action,
        )

    def _record_event(self, event: CallEvent, branch_confidence: float) -> None:
        # Publish to EventBus
        EventBus.publish(OperationalEvent(
            type=EventType.STATE_DISCOVERED if event.intent != "unknown" else EventType.STATE_UNRESOLVED,
            payload={
                "intent": event.intent,
                "node_id": event.node_id,
                "confidence": branch_confidence,
                "dtmf": event.dtmf
            },
            meta=EventMetadata(
                session_id=self.session_id,
                state_id=event.node_id,
                confidence=branch_confidence,
                source_component="live_map"
            )
        ))

        self.ledger.record(event)
        self.mapper.observe(
            event,
            branch_confidence=branch_confidence,
            session_id=self.session_id or "session-1",
        )

    @staticmethod
    def _prompt_confidence(event: CallEvent) -> float:
        if event.kind != "prompt":
            return 1.0

        return classify_prompt(event.text).confidence
