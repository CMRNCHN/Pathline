from typer.testing import CliRunner

from runtime.kernel.cli import app


runner = CliRunner()


def test_dry_run_prints_plan() -> None:
    result = runner.invoke(app, ["dry-run", "--target-number", "+15555550100"])

    assert result.exit_code == 0
    assert "dry run" in result.stdout.lower()