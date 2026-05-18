from typer.testing import CliRunner

from tools.pathline_cli import app


runner = CliRunner()


def test_cli_shows_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "IVR assessor CLI" in result.stdout


def test_cli_version_without_tkinter_dependency():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ivr-assessor" in result.stdout


def test_cli_inspect_replay_outputs_summary():
    result = runner.invoke(
        app,
        [
            "inspect-replay",
            "--trace-path",
            "tests/fixtures/sample_ivr_trace.json",
        ],
    )
    assert result.exit_code == 0
    assert "Replay inspection" in result.stdout
    assert "dtmf_path: 1" in result.stdout


def test_cli_inspect_runtime_reads_metrics_file(tmp_path):
    metrics_path = tmp_path / "runtime_metrics.json"
    metrics_path.write_text(
        """
        {
          "startup": {"events": [{"stage": "gui.ready", "detail": "gui", "t_ms": 11, "ts": 100.011}]},
          "runtime": {"checkpoint_count": 1, "cleanup_count": 0, "last_checkpoint": {"stage": "gui.ready"}, "checkpoints": []},
          "session": {"is_running": false, "target": "", "queue": null, "error": null},
          "stream_server": {"lifecycle_events": []},
          "replay_visibility": {"reports": {}, "recordings": {}, "replays": {}, "snapshots": {}, "recording_artifacts": []},
          "staleness": {"is_stale": false, "idle_for_s": 0.0, "last_activity_at": 100.011},
          "last_session": null
        }
        """.strip(),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["inspect-runtime", "--metrics-path", str(metrics_path)],
    )

    assert result.exit_code == 0
    assert "Runtime diagnostics" in result.stdout
    assert "runtime_checkpoints: 1" in result.stdout