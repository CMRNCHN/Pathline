from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CallEvent:
    kind: str
    text: str
    t_ms: int


@dataclass
class CallPlan:
    target_number: str
    max_depth: int
    max_attempts: int
    dtmf_timeout_ms: int
    response_mode: str
    allowed_branches: list[str] = field(default_factory=list)
    exploration_budget: int = 0
    confidence_threshold: float = 0.0
