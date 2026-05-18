from __future__ import annotations

from dataclasses import dataclass, field

from runtime.state.event_ledger import EventLedger
from runtime.ivr_mapper import IvrMapper, branch_sort_key as _branch_key
from runtime.state.models import CallEvent


@dataclass
class SessionRecord:
    session_id: str
    target_number: str | None = None
    active: bool = True
    ledger: EventLedger = field(default_factory=EventLedger)
    mapper: IvrMapper = field(default_factory=IvrMapper)

    def record_event(self, event: CallEvent, branch_confidence: float) -> None:
        self.ledger.record(event)
        self.mapper.observe(
            event,
            branch_confidence=branch_confidence,
            session_id=self.session_id,
        )

    def graph(self) -> dict[str, dict[str, object]]:
        return self.mapper.graph()


class MultiSessionOrchestrator:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}

    def register_session(
        self,
        session_id: str,
        target_number: str | None = None,
    ) -> SessionRecord:
        session = self._sessions.get(session_id)
        if session is not None:
            if target_number is not None and session.target_number is None:
                session.target_number = target_number
            return session

        session = SessionRecord(session_id=session_id, target_number=target_number)
        self._sessions[session_id] = session
        return session

    def start_session(
        self,
        session_id: str,
        target_number: str | None = None,
    ) -> SessionRecord:
        session = self.register_session(session_id=session_id, target_number=target_number)
        session.active = True
        return session

    def record_event(
        self,
        session_id: str,
        event: CallEvent,
        branch_confidence: float,
    ) -> None:
        session = self._require_session(session_id)
        session.record_event(event, branch_confidence=branch_confidence)

    def combined_graph(self) -> dict[str, dict[str, object]]:
        combined_nodes: dict[str, dict[str, object]] = {}

        for session in self._sessions.values():
            for prompt, node in session.graph().items():
                combined_node = combined_nodes.setdefault(
                    prompt,
                    {
                        "observations": 0,
                        "confidence": 0.0,
                        "sessions": set(),
                        "announced_options": set(),
                        "branches": {},
                    },
                )
                combined_node["observations"] += int(node["observations"])
                combined_node["confidence"] = max(
                    float(combined_node["confidence"]),
                    float(node["confidence"]),
                )
                combined_node["sessions"].update(node["sessions"])
                combined_node["announced_options"].update(
                    node.get("announced_options", []) or []
                )

                for branch, observation in node["branches"].items():
                    branch_node = combined_node["branches"].setdefault(
                        branch,
                        {
                            "count": 0,
                            "confidence": 0.0,
                            "sessions": set(),
                            "next_prompts": set(),
                        },
                    )
                    branch_node["count"] += int(observation["count"])
                    branch_node["confidence"] = max(
                        float(branch_node["confidence"]),
                        float(observation["confidence"]),
                    )
                    branch_node["sessions"].update(observation["sessions"])
                    branch_node["next_prompts"].update(observation["next_prompts"])

        return {
            prompt: {
                "observations": node["observations"],
                "confidence": node["confidence"],
                "sessions": sorted(node["sessions"]),
                "announced_options": sorted(
                    node["announced_options"], key=_branch_key
                ),
                "branches": {
                    branch: {
                        "count": observation["count"],
                        "confidence": observation["confidence"],
                        "sessions": sorted(observation["sessions"]),
                        "next_prompts": sorted(observation["next_prompts"]),
                    }
                    for branch, observation in sorted(
                        node["branches"].items(), key=lambda kv: _branch_key(kv[0])
                    )
                },
            }
            for prompt, node in sorted(combined_nodes.items())
        }

    def session_index(self) -> dict[str, dict[str, object]]:
        return {
            session_id: {
                "session_id": session.session_id,
                "target_number": session.target_number,
                "active": session.active,
                "event_count": len(session.ledger.all()),
                "graph": session.graph(),
            }
            for session_id, session in sorted(self._sessions.items())
        }

    def _require_session(self, session_id: str) -> SessionRecord:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise KeyError(f"Unknown session: {session_id}") from error