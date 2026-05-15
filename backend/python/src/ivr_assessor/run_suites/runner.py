"""SuiteRunner — executes a RunSuite against a live or simulated IVR runtime.

Architecture:
  - Runs in a background thread (matches existing live_map_gui.py pattern).
  - Subscribes to transcript events from the streaming server via callback.
  - Feeds events into a threading.Queue consumed per step.
  - Emits RunSuiteEvents into an output queue consumed by the HTTP poll endpoint.
  - Each step has its own timeout enforced via threading.Event.wait(timeout).

No asyncio in the runner — it bridges the async streaming server to the
synchronous HTTP server via thread-safe queues.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .events import (
    IVREventType,
    IVRRuntimeEvent,
    RunSuiteEvent,
    RunSuiteStartedEvent,
    RunSuiteCompletedEvent,
    ScenarioStartedEvent,
    ScenarioCompletedEvent,
    StepStartedEvent,
    StepUpdatedEvent,
    StepPassedEvent,
    StepFailedEvent,
    StepTimedOutEvent,
)
from .models import (
    RunSuite,
    TestScenario,
    TestStep,
    StepAction,
    StepResult,
    ScenarioResult,
    RunResult,
    SuiteRunStatus,
)
from .status import StepStatus, FailureReason, is_terminal
from .validators import (
    validate_text_contains,
    validate_intent,
    validate_node,
    validate_no_pan_in_log,
    validate_secure_card_token,
    validate_secure_card_deleted,
)

logger = logging.getLogger(__name__)


@dataclass
class _StepContext:
    """Shared runtime state threaded through step execution."""
    result: StepResult
    step: TestStep
    scenario_id: str
    event_queue: "queue.Queue[IVRRuntimeEvent]"
    out_queue: "queue.Queue[RunSuiteEvent]"
    suite_id: str
    telephony: Any | None
    log_lines: list[str]
    secure_card_store: dict[str, Any]


class SuiteRunner:
    """Execute a RunSuite, emitting live step-status events."""

    def __init__(
        self,
        suite: RunSuite,
        telephony: Any | None = None,
        on_event: Callable[[RunSuiteEvent], None] | None = None,
    ) -> None:
        self._suite = suite
        self._telephony = telephony
        self._on_event = on_event

        # Events coming IN from the IVR runtime (transcripts, intents, etc.)
        self._runtime_events: queue.Queue[IVRRuntimeEvent] = queue.Queue()

        # Events going OUT to the UI (step status updates)
        self._output_events: queue.Queue[RunSuiteEvent] = queue.Queue()

        self._run_result: RunResult | None = None
        self._thread: threading.Thread | None = None
        self._abort_event = threading.Event()

        # Per-session state
        self._log_lines: list[str] = []
        self._secure_card_store: dict[str, Any] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def push_runtime_event(self, event: IVRRuntimeEvent) -> None:
        """Called from the streaming server / transcript callback thread."""
        self._runtime_events.put(event)

    def push_transcript(self, text: str, is_final: bool, speech_final: bool) -> None:
        """Convenience bridge: wrap a transcript callback into an IVRRuntimeEvent."""
        if not text.strip():
            return
        self._log_lines.append(f"[transcript] {text}")
        if is_final or speech_final:
            event_type = IVREventType.TRANSCRIPT_FINAL if speech_final else IVREventType.TRANSCRIPT_PARTIAL
            self._runtime_events.put(IVRRuntimeEvent(
                event_type=event_type,
                payload={"text": text, "is_final": is_final, "speech_final": speech_final},
            ))

    def poll_events(self) -> list[dict[str, Any]]:
        """Drain all pending output events (for HTTP poll endpoint)."""
        events = []
        try:
            while True:
                ev = self._output_events.get_nowait()
                events.append(ev.as_ws_message())
        except queue.Empty:
            pass
        return events

    @property
    def run_result(self) -> RunResult | None:
        return self._run_result

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def abort(self) -> None:
        self._abort_event.set()

    def start(self) -> str:
        """Start execution in a background thread. Returns run_id."""
        run_id = str(uuid.uuid4())[:8]
        self._run_result = RunResult(
            suite_id=self._suite.suite_id,
            run_id=run_id,
            name=self._suite.name,
            status=SuiteRunStatus.RUNNING,
            started_at=time.time(),
        )
        self._abort_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return run_id

    # ── Internal runner ───────────────────────────────────────────────────────

    def _emit(self, event: RunSuiteEvent) -> None:
        self._output_events.put(event)
        if self._on_event:
            try:
                self._on_event(event)
            except Exception as exc:
                logger.warning("on_event callback raised: %s", exc)

    def _run(self) -> None:
        result = self._run_result
        assert result is not None

        self._emit(RunSuiteStartedEvent(
            suite_id=self._suite.suite_id,
            run_id=result.run_id,
            name=self._suite.name,
            scenario_count=len(self._suite.scenarios),
        ))

        try:
            for scenario in self._suite.scenarios:
                if self._abort_event.is_set():
                    break
                sc_result = self._run_scenario(scenario, result)
                result.scenario_results.append(sc_result)

            # Final audit: check no PAN in logs
            passed, reason = validate_no_pan_in_log(self._log_lines)
            if not passed:
                result.secure_card_audit.append({
                    "check": "no_raw_pan_in_logs",
                    "passed": False,
                    "reason": reason,
                })
                logger.error("PAN LEAKAGE DETECTED: %s", reason)
            else:
                result.secure_card_audit.append({
                    "check": "no_raw_pan_in_logs",
                    "passed": True,
                })

            result.event_log = [
                e.as_dict() for e in list(self._runtime_events.queue)
            ]
            result.completed_at = time.time()

            total_fail = sum(s.fail_count for s in result.scenario_results)
            result.status = SuiteRunStatus.PASSED if total_fail == 0 else SuiteRunStatus.FAILED

            self._emit(RunSuiteCompletedEvent(
                suite_id=self._suite.suite_id,
                run_id=result.run_id,
                pass_count=result.pass_count,
                fail_count=result.fail_count,
                timeout_count=result.timeout_count,
                duration_ms=result.duration_ms,
                status=result.status.value,
            ))

        except Exception as exc:
            logger.error("Suite runner crashed: %s", exc, exc_info=True)
            result.status = SuiteRunStatus.ERRORED
            result.completed_at = time.time()

    def _run_scenario(
        self, scenario: TestScenario, run_result: RunResult
    ) -> ScenarioResult:
        sc_result = ScenarioResult(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            started_at=time.time(),
        )

        self._emit(ScenarioStartedEvent(
            suite_id=self._suite.suite_id,
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            step_count=len(scenario.steps),
        ))

        for step in scenario.steps:
            if self._abort_event.is_set():
                step_result = StepResult(
                    step_id=step.step_id,
                    action=step.action.value,
                    status=StepStatus.SKIPPED,
                )
                sc_result.step_results.append(step_result)
                continue

            step_result = self._run_step(step, scenario.scenario_id, run_result)
            sc_result.step_results.append(step_result)

            # Stop scenario on first failure (unless step is non-critical check)
            if step_result.status in (StepStatus.FAILED, StepStatus.ERRORED, StepStatus.TIMED_OUT):
                # Mark remaining steps skipped
                remaining_idx = scenario.steps.index(step) + 1
                for remaining in scenario.steps[remaining_idx:]:
                    sc_result.step_results.append(StepResult(
                        step_id=remaining.step_id,
                        action=remaining.action.value,
                        status=StepStatus.SKIPPED,
                    ))
                break

        sc_result.completed_at = time.time()
        sc_result.duration_ms = (sc_result.completed_at - sc_result.started_at) * 1000
        sc_result.passed = sc_result.fail_count == 0

        self._emit(ScenarioCompletedEvent(
            suite_id=self._suite.suite_id,
            scenario_id=scenario.scenario_id,
            passed=sc_result.passed,
            duration_ms=sc_result.duration_ms,
            pass_count=sc_result.pass_count,
            fail_count=sc_result.fail_count,
        ))
        return sc_result

    def _run_step(
        self, step: TestStep, scenario_id: str, run_result: RunResult
    ) -> StepResult:
        result = StepResult(
            step_id=step.step_id,
            action=step.action.value,
            status=StepStatus.RUNNING,
        )

        self._emit(StepStartedEvent(
            suite_id=self._suite.suite_id,
            scenario_id=scenario_id,
            step_id=step.step_id,
            action=step.action.value,
        ))

        ctx = _StepContext(
            result=result,
            step=step,
            scenario_id=scenario_id,
            event_queue=self._runtime_events,
            out_queue=self._output_events,
            suite_id=self._suite.suite_id,
            telephony=self._telephony,
            log_lines=self._log_lines,
            secure_card_store=self._secure_card_store,
        )

        attempts = 0
        max_attempts = step.retry_count + 1
        t_start = time.time()

        while attempts < max_attempts:
            if attempts > 0:
                result.status = StepStatus.RETRYING
                result.retry_attempt = attempts
                self._emit(StepUpdatedEvent(
                    suite_id=self._suite.suite_id,
                    scenario_id=scenario_id,
                    step_id=step.step_id,
                    status=StepStatus.RETRYING.value,
                ))

            try:
                self._execute_step(ctx)
            except _StepTimeout:
                if attempts + 1 >= max_attempts:
                    result.status = StepStatus.TIMED_OUT
                    result.error = f"Timed out after {step.timeout_ms}ms"
                    self._emit(StepTimedOutEvent(
                        suite_id=self._suite.suite_id,
                        scenario_id=scenario_id,
                        step_id=step.step_id,
                        timeout_ms=step.timeout_ms,
                    ))
                    break
            except _StepFailed as exc:
                if attempts + 1 >= max_attempts:
                    result.status = StepStatus.FAILED
                    result.error = str(exc)
                    self._emit(StepFailedEvent(
                        suite_id=self._suite.suite_id,
                        scenario_id=scenario_id,
                        step_id=step.step_id,
                        duration_ms=(time.time() - t_start) * 1000,
                        reason=exc.reason.value,
                        expected=exc.expected,
                        actual=exc.actual,
                        error=str(exc),
                    ))
                    break
            except Exception as exc:
                result.status = StepStatus.ERRORED
                result.error = str(exc)
                logger.error("Step %s errored: %s", step.step_id, exc, exc_info=True)
                self._emit(StepFailedEvent(
                    suite_id=self._suite.suite_id,
                    scenario_id=scenario_id,
                    step_id=step.step_id,
                    duration_ms=(time.time() - t_start) * 1000,
                    reason=FailureReason.UNKNOWN.value,
                    error=str(exc),
                ))
                break
            else:
                # Success
                result.status = StepStatus.PASSED
                result.duration_ms = (time.time() - t_start) * 1000
                self._emit(StepPassedEvent(
                    suite_id=self._suite.suite_id,
                    scenario_id=scenario_id,
                    step_id=step.step_id,
                    duration_ms=result.duration_ms,
                    actual=result.actual_response,
                    confidence=result.confidence,
                ))
                break

            attempts += 1

        if not is_terminal(result.status):
            result.status = StepStatus.ERRORED

        return result

    def _execute_step(self, ctx: _StepContext) -> None:
        """Execute a single step. Raises _StepTimeout or _StepFailed on failure."""
        step = ctx.step
        action = step.action

        if action == StepAction.START_CALL:
            self._step_start_call(ctx)
        elif action == StepAction.WAIT_FOR_PROMPT:
            self._step_wait_for_prompt(ctx)
        elif action == StepAction.SEND_DTMF:
            self._step_send_dtmf(ctx)
        elif action == StepAction.SEND_SPEECH:
            self._step_send_speech(ctx)
        elif action in (StepAction.WAIT_FOR_TRANSCRIPT, StepAction.WAIT_FOR_PROMPT):
            self._step_wait_for_prompt(ctx)
        elif action == StepAction.WAIT_FOR_INTENT:
            self._step_wait_for_event(ctx, IVREventType.INTENT_DETECTED, "intent")
        elif action == StepAction.WAIT_FOR_NODE:
            self._step_wait_for_event(ctx, IVREventType.ROUTE_NODE_ENTERED, "node_id")
        elif action == StepAction.WAIT_FOR_TRANSFER:
            self._step_wait_for_event(ctx, IVREventType.CALL_TRANSFERRED, "to_number")
        elif action == StepAction.CHECK_SECURE_CARD_SAVED:
            self._step_check_secure_card_saved(ctx)
        elif action == StepAction.CHECK_SECURE_CARD_LOOKUP:
            self._step_check_secure_card_lookup(ctx)
        elif action == StepAction.CHECK_SECURE_CARD_DELETED:
            self._step_check_secure_card_deleted(ctx)
        elif action == StepAction.CHECK_NO_RAW_CARD_LOGGED:
            self._step_check_no_pan(ctx)
        elif action == StepAction.CHECK_WEBHOOK_CALLED:
            self._step_check_webhook(ctx)
        elif action == StepAction.END_CALL:
            self._step_end_call(ctx)
        else:
            raise ValueError(f"Unhandled action: {action}")

    # ── Step implementations ──────────────────────────────────────────────────

    def _step_start_call(self, ctx: _StepContext) -> None:
        if ctx.telephony:
            try:
                ctx.telephony.call(
                    self._suite.target_number,
                    stream_url=None,
                )
            except Exception as exc:
                raise _StepFailed(
                    FailureReason.CALL_ERROR, error=str(exc)
                ) from exc

        # Wait for CallStarted event or just pass if no telephony
        if ctx.step.expected_event:
            ev = self._wait_for_event(ctx, ctx.step.expected_event)
            ctx.result.actual_response = ctx.step.expected_event

    def _step_wait_for_prompt(self, ctx: _StepContext) -> None:
        timeout_s = ctx.step.timeout_ms / 1000
        deadline = time.time() + timeout_s

        while time.time() < deadline:
            if self._abort_event.is_set():
                break
            try:
                ev = ctx.event_queue.get(timeout=min(0.5, deadline - time.time()))
            except queue.Empty:
                continue

            if ev.event_type in (IVREventType.TRANSCRIPT_FINAL, IVREventType.TRANSCRIPT_PARTIAL):
                text = ev.payload.get("text", "")
                ctx.result.transcript_snippet = text
                ctx.result.actual_response = text

                if ctx.step.expected_text_contains:
                    ok, reason = validate_text_contains(text, ctx.step.expected_text_contains)
                    if ok:
                        ctx.result.confidence = ev.payload.get("confidence")
                        return
                    # Not a match — keep waiting
                else:
                    # No specific expectation — any transcript passes
                    return

        raise _StepTimeout()

    def _step_send_dtmf(self, ctx: _StepContext) -> None:
        digits = ctx.step.input_value or ""
        self._log_lines.append(f"[dtmf] sending: {digits}")
        if ctx.telephony:
            try:
                ctx.telephony.send_dtmf(None, digits)
            except Exception as exc:
                raise _StepFailed(FailureReason.CALL_ERROR, error=str(exc)) from exc

        ctx.result.actual_response = f"dtmf:{digits}"

        if ctx.step.expected_event:
            ev = self._wait_for_event(ctx, ctx.step.expected_event)
            if ctx.step.expected_intent:
                actual_intent = ev.payload.get("intent")
                ok, reason = validate_intent(actual_intent, ctx.step.expected_intent)
                if not ok:
                    raise _StepFailed(
                        FailureReason.INTENT_MISMATCH,
                        expected=ctx.step.expected_intent,
                        actual=actual_intent,
                        error=reason,
                    )

    def _step_send_speech(self, ctx: _StepContext) -> None:
        text = ctx.step.input_value or ""
        self._log_lines.append(f"[speech] sending: {text}")
        if ctx.telephony:
            try:
                ctx.telephony.say(None, text)
            except Exception as exc:
                raise _StepFailed(FailureReason.CALL_ERROR, error=str(exc)) from exc
        ctx.result.actual_response = f"speech:{text}"

        if ctx.step.expected_event:
            self._wait_for_event(ctx, ctx.step.expected_event)

    def _step_wait_for_event(
        self, ctx: _StepContext, event_type: str, result_field: str
    ) -> None:
        ev = self._wait_for_event(ctx, event_type)
        ctx.result.actual_response = ev.payload.get(result_field, event_type)

        if ctx.step.expected_intent:
            ok, reason = validate_intent(
                ev.payload.get("intent"), ctx.step.expected_intent
            )
            if not ok:
                raise _StepFailed(
                    FailureReason.INTENT_MISMATCH,
                    expected=ctx.step.expected_intent,
                    actual=ev.payload.get("intent"),
                    error=reason,
                )

        if ctx.step.expected_node_id:
            ok, reason = validate_node(
                ev.payload.get("node_id"), ctx.step.expected_node_id
            )
            if not ok:
                raise _StepFailed(
                    FailureReason.NODE_MISMATCH,
                    expected=ctx.step.expected_node_id,
                    actual=ev.payload.get("node_id"),
                    error=reason,
                )

    def _step_check_secure_card_saved(self, ctx: _StepContext) -> None:
        ev = self._wait_for_event(ctx, IVREventType.SECURE_CARD_STORED)
        token = ev.payload.get("token")
        ok, reason = validate_secure_card_token(token)
        if not ok:
            raise _StepFailed(FailureReason.SECURE_CARD_MISSING, error=reason)
        ctx.result.secure_card_token = token
        ctx.result.actual_response = f"token:{token}"
        ctx.secure_card_store["last_token"] = token
        ctx.secure_card_store["metadata"] = {
            "brand": ev.payload.get("brand"),
            "last4": ev.payload.get("last4"),
            "status": ev.payload.get("status"),
            "created_at": ev.payload.get("created_at"),
        }

    def _step_check_secure_card_lookup(self, ctx: _StepContext) -> None:
        ev = self._wait_for_event(ctx, IVREventType.SECURE_CARD_LOOKUP)
        token = ev.payload.get("token")
        ok, reason = validate_secure_card_token(token)
        if not ok:
            raise _StepFailed(FailureReason.SECURE_CARD_MISSING, error=reason)
        ctx.result.secure_card_token = token
        ctx.result.actual_response = f"lookup:token:{token}"

    def _step_check_secure_card_deleted(self, ctx: _StepContext) -> None:
        ev = self._wait_for_event(ctx, IVREventType.SECURE_CARD_DELETED)
        deleted = ev.payload.get("deleted", False)
        ok, reason = validate_secure_card_deleted(deleted)
        if not ok:
            raise _StepFailed(FailureReason.SECURE_CARD_NOT_DELETED, error=reason)
        ctx.result.actual_response = "card_deleted:ok"

    def _step_check_no_pan(self, ctx: _StepContext) -> None:
        ok, reason = validate_no_pan_in_log(ctx.log_lines)
        if not ok:
            raise _StepFailed(FailureReason.PAN_LEAKED, error=reason)
        ctx.result.actual_response = "no_pan_in_logs:ok"

    def _step_check_webhook(self, ctx: _StepContext) -> None:
        # Webhook validation: wait for a synthetic CheckWebhookCalled event
        # that the caller injects when their webhook endpoint is hit.
        try:
            ev = self._wait_for_event(ctx, "WebhookCalled")
            ctx.result.actual_response = f"webhook:{ev.payload.get('endpoint', 'called')}"
        except _StepTimeout:
            raise _StepFailed(FailureReason.WEBHOOK_NOT_CALLED, error="Webhook was not called within timeout")

    def _step_end_call(self, ctx: _StepContext) -> None:
        if ctx.telephony:
            try:
                ctx.telephony.hangup(None)
            except Exception:
                pass
        ctx.result.actual_response = "call_ended"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _wait_for_event(self, ctx: _StepContext, expected_type: str) -> IVRRuntimeEvent:
        """Drain the event queue until we see expected_type or timeout."""
        timeout_s = ctx.step.timeout_ms / 1000
        deadline = time.time() + timeout_s

        while time.time() < deadline:
            if self._abort_event.is_set():
                raise _StepTimeout()
            try:
                ev = ctx.event_queue.get(timeout=min(0.5, deadline - time.time()))
            except queue.Empty:
                continue
            if ev.event_type == expected_type:
                return ev
            # Re-queue non-matching events so other steps can see them
            # (use a small temp list to avoid infinite loop)
            ctx.event_queue.put(ev)
            time.sleep(0.01)  # yield to avoid spin-lock

        raise _StepTimeout()


# ── Internal exceptions ───────────────────────────────────────────────────────

class _StepTimeout(Exception):
    pass


class _StepFailed(Exception):
    def __init__(
        self,
        reason: FailureReason,
        expected: str | None = None,
        actual: str | None = None,
        error: str | None = None,
    ) -> None:
        self.reason = reason
        self.expected = expected
        self.actual = actual
        self.error = error
        super().__init__(error or reason.value)
