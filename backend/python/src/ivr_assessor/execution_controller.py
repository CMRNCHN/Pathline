from __future__ import annotations


class ExecutionController:
    def __init__(self, allowlist: list[str]) -> None:
        self._allowlist = set(allowlist)

    def can_dial(self, target_number: str) -> bool:
        return target_number in self._allowlist
