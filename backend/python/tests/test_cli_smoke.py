from typer.testing import CliRunner

from ivr_assessor.cli import app


runner = CliRunner()


def test_cli_shows_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "IVR assessor CLI" in result.stdout


def test_cli_version_without_tkinter_dependency():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ivr-assessor" in result.stdout
