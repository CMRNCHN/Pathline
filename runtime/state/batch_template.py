from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Mapping, Sequence

from runtime.state.call_template import (
    CallTemplatePlan,
    InjectionActionKind,
    InjectionMode,
    TemplateStyle,
    build_call_template_plan,
)
from runtime.ivr_mapper import IvrMapper
from runtime.state.live_map import RecordingTelephonyClient
from runtime.state.models import CallEvent
from runtime.telephony import TelephonyClient


@dataclass(frozen=True)
class BatchEntry:
    label: str
    target_number: str
    field_values: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchEntryResult:
    label: str
    target_number: str
    session_id: str
    plan: dict[str, object]
    transcript: list[dict[str, object]]
    graph: dict[str, dict[str, object]]
    last_action: str | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BatchRunResult:
    style: str
    default_mode: str
    entries: list[BatchEntryResult]

    def as_dict(self) -> dict[str, object]:
        return {
            "style": self.style,
            "default_mode": self.default_mode,
            "entries": [entry.as_dict() for entry in self.entries],
        }


def run_batch_template(
    *,
    base_fields: Mapping[str, str],
    entries: Sequence[BatchEntry],
    default_mode: InjectionMode = InjectionMode.DTMF,
    style: TemplateStyle = TemplateStyle.PRO_AUDIO_WORKSTATION,
    telephony: TelephonyClient | None = None,
) -> BatchRunResult:
    client = telephony or RecordingTelephonyClient()
    results: list[BatchEntryResult] = []

    for entry in entries:
        merged = {**dict(base_fields), **dict(entry.field_values)}
        plan = build_call_template_plan(
            target_number=entry.target_number,
            fields=merged,
            default_mode=default_mode,
            style=style,
        )
        result = _execute_plan(entry=entry, plan=plan, telephony=client)
        results.append(result)

    return BatchRunResult(
        style=style.value,
        default_mode=default_mode.value,
        entries=results,
    )


def _execute_plan(
    *,
    entry: BatchEntry,
    plan: CallTemplatePlan,
    telephony: TelephonyClient,
) -> BatchEntryResult:
    session_id = telephony.dial(entry.target_number)
    mapper = IvrMapper()
    transcript: list[dict[str, object]] = []
    last_action: str | None = None

    def record(event: CallEvent, confidence: float) -> None:
        transcript.append({"kind": event.kind, "text": event.text, "t_ms": event.t_ms})
        mapper.observe(event, branch_confidence=confidence, session_id=session_id)

    for step in plan.steps:
        prompt_event = CallEvent(kind="prompt", text=step.prompt, t_ms=step.t_ms)
        record(prompt_event, confidence=0.9)

        if step.action == InjectionActionKind.SEND_DTMF and step.value:
            telephony.send_dtmf(session_id, step.value)
            last_action = f"dtmf:{step.value}"
            record(CallEvent(kind="action", text=last_action, t_ms=step.t_ms + 10), confidence=1.0)
        elif step.action == InjectionActionKind.SPEAK and step.value:
            telephony.say(session_id, step.value)
            last_action = f"speak:{step.value}"
            record(CallEvent(kind="action", text=last_action, t_ms=step.t_ms + 10), confidence=1.0)

    telephony.hangup(session_id)

    return BatchEntryResult(
        label=entry.label,
        target_number=entry.target_number,
        session_id=session_id,
        plan=plan.as_dict(),
        transcript=transcript,
        graph=mapper.graph(),
        last_action=last_action,
    )


def batch_entries_from_payload(payload: Sequence[Mapping[str, object]]) -> list[BatchEntry]:
    parsed: list[BatchEntry] = []
    for index, item in enumerate(payload):
        target = item.get("target_number")
        if not isinstance(target, str) or not target:
            raise ValueError(f"entry[{index}] missing target_number")
        label = item.get("label")
        if not isinstance(label, str) or not label:
            label = f"entry-{index + 1}"
        raw_values = item.get("field_values") or {}
        if not isinstance(raw_values, Mapping):
            raise ValueError(f"entry[{index}] field_values must be an object")
        field_values = {str(key): str(value) for key, value in raw_values.items()}
        parsed.append(
            BatchEntry(label=label, target_number=target, field_values=field_values)
        )
    return parsed