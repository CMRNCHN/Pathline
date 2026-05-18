from __future__ import annotations

from runtime.state.models import CallEvent


class EventLedger:
    def __init__(self) -> None:
        self._events: list[CallEvent] = []

    def record(self, event: CallEvent) -> None:
        self._events.append(event)

    def all(self) -> list[CallEvent]:
        return list(self._events)