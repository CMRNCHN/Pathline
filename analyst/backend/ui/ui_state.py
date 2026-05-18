from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from runtime.state.live_map import LiveMappingSession
    from analyst.telecom.run_suites.runner import SuiteRunner
    from runtime.transport.streaming_server import StreamingServer

from infrastructure.config.paths import (
    BASE_DIR as _DATA,
    SUITES_DIR,
    RUN_SUITES_DIR,
    REPORTS_DIR,
    RUN_SUITE_REPORTS_DIR,
    RECORDINGS_DIR,
    REPLAYS_DIR,
    SNAPSHOTS_DIR,
    BENCHMARKS_DIR,
    EVENTS_DIR,
    ANNOTATIONS_DIR,
    SNAPSHOT_INTERVAL
)
WAVEFORMS_DIR      = _DATA / "waveforms"
EVIDENCE_BUNDLES_DIR = _DATA / "evidence_bundles"


class ObservableQueue(queue.Queue):
    def __init__(self) -> None:
        super().__init__()
        self._metrics_lock = threading.Lock()
        self._puts_total = 0
        self._gets_total = 0
        self._max_depth_seen = 0
        self._last_put_at: float | None = None
        self._last_get_at: float | None = None

    def put(self, item: Any, block: bool = True, timeout: float | None = None) -> None:
        super().put(item, block=block, timeout=timeout)
        depth = self.qsize()
        with self._metrics_lock:
            self._puts_total += 1
            self._max_depth_seen = max(self._max_depth_seen, depth)
            self._last_put_at = time.time()

    def get(self, block: bool = True, timeout: float | None = None) -> Any:
        item = super().get(block=block, timeout=timeout)
        with self._metrics_lock:
            self._gets_total += 1
            self._last_get_at = time.time()
        return item

    def metrics(self) -> dict[str, int | float | str | None]:
        with self._metrics_lock:
            m = {
                "current_depth": self.qsize(),
                "puts_total": self._puts_total,
                "gets_total": self._gets_total,
                "max_depth_seen": self._max_depth_seen,
                "last_put_at": self._last_put_at,
                "last_get_at": self._last_get_at,
            }
            try:
                from runtime.events.event_sink import sink
                m.update(sink.metrics())
            except ImportError:
                pass
            return m


@dataclass
class QueuePromptSource:
    prompt_queue: ObservableQueue = field(default_factory=ObservableQueue)
    _t_start: float = field(default_factory=time.time)

    def next_event(self, session_id: str) -> Any:  # noqa: ARG002
        from runtime.state.models import CallEvent
        text = self.prompt_queue.get()
        if text is None:
            return None
        t_ms = int((time.time() - self._t_start) * 1000)
        return CallEvent(kind="prompt", text=text, t_ms=t_ms)

    def elapsed_ms(self) -> int:
        return int((time.time() - self._t_start) * 1000)

    def metrics(self) -> dict[str, int | float | None]:
        metrics = self.prompt_queue.metrics()
        metrics["elapsed_ms"] = self.elapsed_ms()
        return metrics


class AppState:
    _MAX_RUNTIME_CHECKPOINTS = 64

    def __init__(self) -> None:
        self.session: LiveMappingSession | None = None
        self.source: QueuePromptSource | None = None
        self.streaming_server: StreamingServer | None = None
        self.logs: list[str] = []
        self.is_running: bool = False
        self.ledger_idx: int = 0
        self.graph: dict = {}
        self.target: str = ""
        self.start_time: float | None = None
        self.error: str | None = None
        self.live_caption: str = ""
        self.startup_t0: float | None = None
        self.startup_events: list[dict[str, Any]] = []
        self.runtime_sequence: int = 0
        self.runtime_checkpoints: list[dict[str, Any]] = []
        self.reset_count: int = 0
        self.last_reset_at: float | None = None
        self.last_session_snapshot: dict[str, Any] | None = None

    def reset(self) -> None:
        self.reset_count += 1
        self.last_reset_at = time.time()
        self.record_runtime_checkpoint(
            "state.reset",
            "resetting runtime state",
            category="state",
            reset_count=self.reset_count,
        )
        self.session = None
        self.source = None
        self.streaming_server = None
        self.logs = []
        self.is_running = False
        self.ledger_idx = 0
        self.graph = {}
        self.target = ""
        self.start_time = None
        self.error = None
        self.live_caption = ""
        self.last_session_snapshot = None

    def drain_logs(self) -> list[str]:
        logs, self.logs = self.logs, []
        return logs

    def begin_startup_trace(self) -> None:
        self.runtime_sequence += 1
        self.startup_t0 = time.monotonic()
        self.startup_events = []
        self.runtime_checkpoints = []

    def record_startup_event(self, stage: str, detail: str = "", **extra: Any) -> None:
        now = time.monotonic()
        t0 = self.startup_t0 or now
        event: dict[str, Any] = {
            "stage": stage,
            "detail": detail,
            "t_ms": int((now - t0) * 1000),
            "ts": time.time(),
        }
        event.update(extra)
        self.startup_events.append(event)

    def startup_snapshot(self) -> dict[str, Any]:
        return {
            "event_count": len(self.startup_events),
            "events": list(self.startup_events),
        }

    def record_runtime_checkpoint(
        self,
        stage: str,
        detail: str = "",
        *,
        category: str = "runtime",
        **extra: Any,
    ) -> None:
        now = time.monotonic()
        t0 = self.startup_t0 or now
        checkpoint: dict[str, Any] = {
            "seq": len(self.runtime_checkpoints) + 1,
            "launch_sequence": self.runtime_sequence,
            "category": category,
            "stage": stage,
            "detail": detail,
            "t_ms": int((now - t0) * 1000),
            "ts": time.time(),
        }
        checkpoint.update(extra)
        self.runtime_checkpoints.append(checkpoint)
        self.runtime_checkpoints = self.runtime_checkpoints[-self._MAX_RUNTIME_CHECKPOINTS:]

    def record_cleanup_event(self, stage: str, detail: str = "", **extra: Any) -> None:
        self.record_runtime_checkpoint(stage, detail, category="cleanup", **extra)

    def runtime_checkpoint_snapshot(self) -> dict[str, Any]:
        last_checkpoint = self.runtime_checkpoints[-1] if self.runtime_checkpoints else None
        cleanup_count = sum(
            1 for checkpoint in self.runtime_checkpoints if checkpoint.get("category") == "cleanup"
        )
        return {
            "launch_sequence": self.runtime_sequence,
            "checkpoint_count": len(self.runtime_checkpoints),
            "cleanup_count": cleanup_count,
            "reset_count": self.reset_count,
            "last_reset_at": self.last_reset_at,
            "last_checkpoint": dict(last_checkpoint) if last_checkpoint else None,
            "checkpoints": list(self.runtime_checkpoints),
        }

    def active_prompt(self) -> str | None:
        if self.session is None:
            return None
        for evt in reversed(self.session.ledger.all()):
            if evt.kind == "prompt":
                return evt.text
        return None


class RunSuiteState:
    """Holds the active SuiteRunner and its result for the HTTP poll layer."""

    def __init__(self) -> None:
        self._runner: SuiteRunner | None = None
        self._lock = threading.Lock()

    def set_runner(self, runner: SuiteRunner) -> None:
        with self._lock:
            self._runner = runner

    def get_runner(self) -> SuiteRunner | None:
        with self._lock:
            return self._runner

    def poll(self) -> list[dict]:
        runner = self.get_runner()
        if runner is None:
            return []
        return runner.poll_events()

    def abort(self) -> None:
        runner = self.get_runner()
        if runner:
            runner.abort()


# Storage Layout: ~/.ivr_assessor/test_runs/YYYY-MM-DD/<test_id>/manifest.json
TEST_RUNS_DIR      = _DATA / "test_runs"
STATE = AppState()
RS_STATE = RunSuiteState()