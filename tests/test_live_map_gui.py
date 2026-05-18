import pytest

from analyst.backend.ui.ui_state import STATE
from analyst.backend.live_map_gui import _normalize_suite_filename, _runtime_diagnostics_payload


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("billing_suite", "billing_suite.json"),
        ("billing-suite.json", "billing-suite.json"),
        ("suite.v1", "suite.v1.json"),
        ("suite_01.JSON", "suite_01.JSON.json"),
        ("  nightly_suite  ", "nightly_suite.json"),
    ],
)
def test_normalize_suite_filename_accepts_safe_names(raw: str, expected: str) -> None:
    assert _normalize_suite_filename(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "../escape",
        "..\\escape",
        "nested/path",
        "nested\\path",
        ".json",
        "suite name",
        "suite$",
    ],
)
def test_normalize_suite_filename_rejects_unsafe_names(raw: object) -> None:
    with pytest.raises(ValueError):
        _normalize_suite_filename(raw)


def test_runtime_diagnostics_payload_uses_last_session_snapshot() -> None:
    previous_snapshot = STATE.last_session_snapshot
    previous_target = STATE.target
    previous_error = STATE.error
    previous_start_time = STATE.start_time
    previous_session = STATE.session
    previous_source = STATE.source
    previous_running = STATE.is_running
    try:
        STATE.last_session_snapshot = {
            "target": "+15555550100",
            "started_at": 100.0,
            "ended_at": 101.0,
            "duration_ms": 1000,
            "manual_mode": False,
            "event_count": 1,
            "events": [{"seq": 1, "kind": "prompt", "text": "Press 1", "t_ms": 0}],
            "graph_node_count": 1,
            "queue": {"current_depth": 0, "max_depth_seen": 1, "puts_total": 1, "gets_total": 1},
            "error": None,
        }
        STATE.target = ""
        STATE.error = None
        STATE.start_time = None
        STATE.session = None
        STATE.source = None
        STATE.is_running = False

        payload = _runtime_diagnostics_payload()

        assert payload["summary"]["session_target"] == "+15555550100"
        assert payload["replay_diagnostics"]["session"]["event_count"] == 1
    finally:
        STATE.last_session_snapshot = previous_snapshot
        STATE.target = previous_target
        STATE.error = previous_error
        STATE.start_time = previous_start_time
        STATE.session = previous_session
        STATE.source = previous_source
        STATE.is_running = previous_running