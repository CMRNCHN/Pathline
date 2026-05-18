from __future__ import annotations

from dataclasses import dataclass

from runtime.state.models import CallEvent


@dataclass(frozen=True)
class Report:
    text: str
    sections: list[str]


def build_report(events: list[CallEvent]) -> Report:
    lines = ["IVR Assessment Report", "", "timeline"]
    for event in events:
        lines.append(f"{event.t_ms:06d} {event.kind}: {event.text}")

    findings = _build_findings(events)
    lines.extend(["", "findings"])
    lines.extend(findings or ["No notable findings"])

    return Report(text="\n".join(lines), sections=["timeline", "findings"])


def _build_findings(events: list[CallEvent]) -> list[str]:
    findings: list[str] = []
    for event in events:
        if event.kind == "prompt" and "press" in event.text.lower():
            findings.append(f"Observed menu prompt at {event.t_ms} ms")
    return findings