import json
from pathlib import Path

from typer.testing import CliRunner

from ivr_assessor.batch_template import BatchEntry, run_batch_template
from ivr_assessor.cli import app
from ivr_assessor.live_map import RecordingTelephonyClient


runner = CliRunner()


def test_run_batch_template_executes_entries_sequentially() -> None:
    telephony = RecordingTelephonyClient()
    result = run_batch_template(
        base_fields={"account_id": "12345"},
        entries=[
            BatchEntry(label="alice", target_number="+15551110001", field_values={"pin": "0001"}),
            BatchEntry(label="bob", target_number="+15551110002", field_values={"pin": "0002"}),
        ],
        telephony=telephony,
    )

    assert [entry.label for entry in result.entries] == ["alice", "bob"]
    assert [target for target, _ in telephony.dialed] == ["+15551110001", "+15551110002"]

    alice = result.entries[0]
    digits_sent = [digits for sid, digits in telephony.dtmf_sent if sid == alice.session_id]
    assert "+15551110001" in digits_sent
    assert "12345" in digits_sent
    assert "0001" in digits_sent

    transcript_kinds = [event["kind"] for event in alice.transcript]
    assert "prompt" in transcript_kinds
    assert "action" in transcript_kinds
    assert alice.last_action is not None and alice.last_action.startswith("dtmf:")
    assert alice.graph, "expected ivr mapper graph nodes"


def test_batch_template_cli_emits_json(tmp_path: Path) -> None:
    config = tmp_path / "batch.json"
    config.write_text(
        json.dumps(
            {
                "base_fields": {"account_id": "999"},
                "entries": [
                    {"label": "first", "target_number": "+15550001", "field_values": {"pin": "1"}},
                    {"label": "second", "target_number": "+15550002", "field_values": {"pin": "2"}},
                ],
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "out.json"
    result = runner.invoke(
        app, ["batch-template", "--config", str(config), "--output", str(output)]
    )

    assert result.exit_code == 0, result.output
    blob = json.loads(output.read_text(encoding="utf-8"))
    assert blob["default_mode"] == "dtmf"
    assert [entry["label"] for entry in blob["entries"]] == ["first", "second"]
    assert blob["entries"][0]["transcript"]
    assert blob["entries"][0]["graph"]
