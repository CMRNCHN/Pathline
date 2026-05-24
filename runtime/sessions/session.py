from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from runtime.mapping.flow_builder import FlowMapBuilder


@dataclass
class CallSession:
    call_sid: str
    phone_number: str = ""
    suite_name: str = ""
    started_at: float = field(default_factory=time.time)
    transcript_segments: list[dict] = field(default_factory=list)
    dtmf_injections: list[dict] = field(default_factory=list)
    voice_injections: list[dict] = field(default_factory=list)
    flow_map: FlowMapBuilder = field(default_factory=FlowMapBuilder)
    active: bool = True


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, CallSession] = {}

    def create_session(
        self,
        call_sid: str,
        phone_number: str = "",
        suite_name: str = "",
    ) -> CallSession:
        session = CallSession(
            call_sid=call_sid,
            phone_number=phone_number,
            suite_name=suite_name,
        )
        self._sessions[call_sid] = session
        return session

    def get_session(self, call_sid: str) -> CallSession | None:
        return self._sessions.get(call_sid)

    def get_or_create(self, call_sid: str, **kwargs: Any) -> CallSession:
        session = self._sessions.get(call_sid)
        if session is None:
            session = self.create_session(call_sid, **kwargs)
        return session

    def get_active_sessions(self) -> list[CallSession]:
        return [s for s in self._sessions.values() if s.active]

    def add_transcript_segment(self, call_sid: str, segment: dict) -> None:
        session = self.get_or_create(call_sid)
        session.transcript_segments.append(segment)
        label = segment.get("text", "")[:60]
        if label:
            session.flow_map.add_node(label=label, transcript=label)

    def record_dtmf_injection(self, call_sid: str, dtmf: str) -> None:
        session = self.get_or_create(call_sid)
        session.dtmf_injections.append({"dtmf": dtmf, "at": time.time()})

    def record_voice_injection(self, call_sid: str, text: str) -> None:
        session = self.get_or_create(call_sid)
        session.voice_injections.append({"text": text, "at": time.time()})

    def update_map(self, call_sid: str, label: str, **kwargs: Any) -> None:
        session = self.get_or_create(call_sid)
        session.flow_map.add_node(label=label, **kwargs)

    def close_session(self, call_sid: str) -> None:
        session = self._sessions.get(call_sid)
        if session:
            session.active = False

    def to_session_dict(self, session: CallSession) -> dict:
        return {
            "call_sid": session.call_sid,
            "phone_number": session.phone_number,
            "suite_name": session.suite_name,
            "started_at": session.started_at,
            "transcript_segments": session.transcript_segments,
            "dtmf_injections": session.dtmf_injections,
            "voice_injections": session.voice_injections,
            "active": session.active,
        }
