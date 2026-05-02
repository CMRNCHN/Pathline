from pathlib import Path

from ivr_assessor.replay_mode import replay_trace


def test_replay_trace_reconstructs_known_billing_path() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "sample_ivr_trace.json"
    result = replay_trace(fixture)

    assert result.summary["event_count"] == 3
    assert result.summary["prompt_count"] == 2
    assert result.summary["action_count"] == 1
    assert "Press 1 for billing" in result.graph
    assert result.graph["Press 1 for billing"]["branches"]["1"]["next_prompts"] == [
        "Billing menu"
    ]
    assert "Billing menu" in result.report.text


def test_replay_trace_accepts_parsed_event_data() -> None:
    result = replay_trace(
        [
            {"kind": "prompt", "text": "Press 1 for billing", "t_ms": 0},
            {"kind": "action", "text": "dtmf:1", "t_ms": 150},
            {"kind": "prompt", "text": "Billing menu", "t_ms": 300},
        ]
    )

    assert result.summary["node_count"] == 2
    assert result.summary["root_prompts"] == ["Billing menu", "Press 1 for billing"]
