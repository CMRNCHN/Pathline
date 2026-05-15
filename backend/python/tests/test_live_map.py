import json

from typer.testing import CliRunner

from ivr_assessor.cli import app
from ivr_assessor.live_map import (
    LiveMappingSession,
    RecordingTelephonyClient,
    ScriptedPromptSource,
    build_default_response_library,
)
from ivr_assessor.models import CallEvent


runner = CliRunner()


def test_single_session_records_prompt_action_and_next_prompt_path() -> None:
    telephony = RecordingTelephonyClient()
    prompt_source = ScriptedPromptSource(
        [
            CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0),
            CallEvent(kind="prompt", text="Billing menu", t_ms=300),
        ]
    )

    session = LiveMappingSession(
        target_number="+15555550100",
        response_mode="dtmf",
        prompt_source=prompt_source,
        telephony=telephony,
        response_library=build_default_response_library("general"),
    )

    summary = session.run()

    assert telephony.dialed == [("+15555550100", "session-1")]
    assert telephony.dtmf_sent == [("session-1", "1")]
    assert telephony.clips_played == []
    assert telephony.hung_up == ["session-1"]
    assert [event["kind"] for event in summary.events] == ["prompt", "action", "prompt"]
    assert summary.graph["Press 1 for billing"]["branches"]["1"]["next_prompts"] == [
        "Billing menu"
    ]
    assert json.dumps(summary.as_dict())


def test_voice_mode_uses_prebuilt_clip_from_response_library() -> None:
    telephony = RecordingTelephonyClient()
    prompt_source = ScriptedPromptSource(
        [CallEvent(kind="prompt", text="Please say your account type", t_ms=0)]
    )

    session = LiveMappingSession(
        target_number="+15555550101",
        response_mode="voice",
        prompt_source=prompt_source,
        telephony=telephony,
        response_library=build_default_response_library("general", response_style="warm"),
        response_label="general",
        response_style="warm",
    )

    summary = session.run()

    assert telephony.dialed == [("+15555550101", "session-1")]
    assert telephony.clips_played == [("session-1", "responses/general.wav")]
    assert summary.last_action == "play:general-warm"


def test_map_command_runs_single_session_and_returns_graph_snapshot() -> None:
    result = runner.invoke(
        app,
        [
            "map",
            "--target-number",
            "+15555550102",
            "--response-mode",
            "dtmf",
            "--prompt",
            "Press 1 for billing",
            "--prompt",
            "Billing menu",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["target_number"] == "+15555550102"
    assert payload["graph"]["Press 1 for billing"]["branches"]["1"]["next_prompts"] == [
        "Billing menu"
    ]


def test_map_command_runs_multi_session_and_returns_combined_graph() -> None:
    result = runner.invoke(
        app,
        [
            "map",
            "--session-mode",
            "multi-session",
            "--target-number",
            "+15555550110",
            "--target-number",
            "+15555550111",
            "--response-mode",
            "dtmf",
            "--prompt",
            "Press 1 for billing",
            "--prompt",
            "Billing menu",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["session_mode"] == "multi-session"
    assert payload["graph"]["Press 1 for billing"]["branches"]["1"]["count"] == 2
    assert payload["session_index"]["session-1"]["target_number"] == "+15555550110"
    assert payload["session_index"]["session-2"]["target_number"] == "+15555550111"
