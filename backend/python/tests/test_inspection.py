from pathlib import Path

from ivr_assessor.inspection import (
    build_runtime_diagnostics,
    inspect_replay_artifact,
)


def test_inspect_replay_artifact_builds_summary_and_chronology() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "sample_ivr_trace.json"

    payload = inspect_replay_artifact(fixture)

    assert payload["source"]["name"] == "sample_ivr_trace.json"
    assert payload["summary"]["event_count"] == 3
    assert payload["summary"]["dtmf_path"] == ["1"]
    assert payload["summary"]["largest_gap_ms"] == 150
    assert payload["chronology"][1]["delta_ms"] == 150
    assert payload["chronology"][2]["text_preview"] == "Billing menu"


def test_build_runtime_diagnostics_combines_session_and_lifecycle_views() -> None:
    runtime_metrics = {
        "startup": {
            "events": [
                {"stage": "bootstrap.ready", "detail": "boot", "t_ms": 5, "ts": 100.0},
                {"stage": "gui.ready", "detail": "gui", "t_ms": 12, "ts": 100.012},
            ]
        },
        "runtime": {
            "checkpoint_count": 3,
            "cleanup_count": 1,
            "last_checkpoint": {"stage": "session.run_complete", "ts": 104.0},
            "checkpoints": [
                {"stage": "launch.begin", "detail": "launch", "category": "startup", "t_ms": 0, "ts": 100.0},
                {"stage": "session.thread_start", "detail": "target=+1555", "category": "session", "t_ms": 400, "ts": 100.4},
                {"stage": "session.run_complete", "detail": "done", "category": "session", "t_ms": 4000, "ts": 104.0},
            ],
        },
        "session": {
            "is_running": False,
            "target": "+15555550100",
            "elapsed_ms": None,
            "ledger_events": 0,
            "queue": None,
            "error": None,
        },
        "stream_server": {
            "last_stream_connected_at": 101.0,
            "last_stream_disconnect_reason": "stop_event",
            "last_stream_close_code": 1000,
            "last_listen_disconnect_reason": "",
            "last_listen_close_code": None,
            "lifecycle_events": [
                {"endpoint": "/stream", "phase": "accepted", "ts": 101.0, "uptime_ms": 900},
                {"endpoint": "/stream", "phase": "start_event", "ts": 101.1, "uptime_ms": 1000},
                {"endpoint": "/listen", "phase": "accepted", "ts": 101.2, "uptime_ms": 1100},
            ],
        },
        "replay_visibility": {
            "reports": {"file_count": 1},
            "recordings": {"file_count": 2},
            "replays": {"file_count": 3},
            "snapshots": {"file_count": 4},
            "recording_artifacts": [{"recording_sid": "RE123", "status": "completed"}],
        },
        "staleness": {
            "last_activity_at": 104.0,
            "idle_for_s": 3.5,
            "is_stale": False,
        },
        "last_session": {
            "target": "+15555550100",
            "started_at": 101.5,
            "ended_at": 104.5,
            "duration_ms": 3000,
            "manual_mode": False,
            "event_count": 3,
            "events": [
                {"seq": 1, "kind": "prompt", "text": "Press 1 for billing", "t_ms": 0},
                {"seq": 2, "kind": "action", "text": "dtmf:1", "t_ms": 120},
                {"seq": 3, "kind": "prompt", "text": "Billing menu", "t_ms": 450},
            ],
            "graph_node_count": 2,
            "queue": {"current_depth": 0, "max_depth_seen": 1, "puts_total": 1, "gets_total": 1},
            "error": None,
        },
    }

    payload = build_runtime_diagnostics(runtime_metrics)

    assert payload["summary"]["session_event_count"] == 3
    assert payload["summary"]["runtime_checkpoint_count"] == 3
    assert payload["queue_visibility"]["session_queue"]["max_depth_seen"] == 1
    assert payload["websocket_lifecycle"]["counts"]["/stream:accepted"] == 1
    assert payload["correlation"]["startup_to_gui_ready_ms"] == 12
    assert payload["correlation"]["session_start_to_first_action_ms"] == 120
    assert payload["replay_diagnostics"]["session"]["graph_node_count"] == 2
    assert any(entry["source"] == "session_event" for entry in payload["timeline"])
