"""Generate JSON and Markdown reports from RunResult."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import RunResult, StepResult, ScenarioResult
from .status import StepStatus
from ..backend.ui.ui_state import RUN_SUITE_REPORTS_DIR as _REPORTS_DIR


def _status_emoji(status: str) -> str:
    return {
        "passed": "✅",
        "failed": "❌",
        "timed_out": "⏱",
        "skipped": "⏭",
        "errored": "💥",
        "running": "▶",
        "retrying": "🔄",
        "pending": "⏳",
    }.get(status, "•")


class RunReport:
    """Formats and saves a RunResult as JSON and Markdown."""

    def __init__(self, result: RunResult) -> None:
        self._result = result

    def as_json(self) -> str:
        return json.dumps(self._result.as_dict(), indent=2)

    def as_markdown(self) -> str:
        r = self._result
        ts = datetime.fromtimestamp(r.started_at, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total_steps = sum(
            len(sc.step_results) for sc in r.scenario_results
        )
        lines = [
            f"# Run Suite Report — {r.name}",
            f"**Suite ID:** `{r.suite_id}`  **Run ID:** `{r.run_id}`",
            f"**Started:** {ts}  **Duration:** {r.duration_ms:.0f} ms",
            f"**Status:** {_status_emoji(r.status.value)} {r.status.value.upper()}",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Scenarios | {len(r.scenario_results)} |",
            f"| Steps | {total_steps} |",
            f"| Passed | {r.pass_count} |",
            f"| Failed | {r.fail_count} |",
            f"| Timed out | {r.timeout_count} |",
            f"| Skipped | {sum(1 for sc in r.scenario_results for st in sc.step_results if st.status == StepStatus.SKIPPED)} |",
            "",
        ]

        # Secure card audit
        if r.secure_card_audit:
            lines += ["## Secure Card Audit", ""]
            for audit in r.secure_card_audit:
                icon = "✅" if audit.get("passed") else "❌"
                lines.append(f"- {icon} `{audit.get('check')}` — {audit.get('reason', 'ok')}")
            lines.append("")

        # Failed steps summary
        failed = r.failed_steps
        if failed:
            lines += ["## Failed Steps", ""]
            for s in failed:
                icon = _status_emoji(s["status"])
                lines.append(
                    f"- {icon} **{s['scenario_id']} / {s['step_id']}** "
                    f"({s['status']}): {s.get('error', '')}"
                )
            lines.append("")

        # Scenario details
        lines.append("## Scenario Results")
        for sc in r.scenario_results:
            icon = "✅" if sc.passed else "❌"
            lines += [
                "",
                f"### {icon} {sc.name} (`{sc.scenario_id}`)",
                f"Duration: {sc.duration_ms:.0f} ms | Passed: {sc.pass_count} | Failed: {sc.fail_count}",
                "",
                "| Step | Action | Status | Duration | Actual Response | Error |",
                "|---|---|---|---|---|---|",
            ]
            for st in sc.step_results:
                icon2 = _status_emoji(st.status.value)
                dur = f"{st.duration_ms:.0f} ms" if st.duration_ms is not None else "—"
                actual = (st.actual_response or "")[:60].replace("|", "\\|")
                error = (st.error or "")[:80].replace("|", "\\|")
                lines.append(
                    f"| `{st.step_id}` | `{st.action}` | {icon2} {st.status.value} "
                    f"| {dur} | {actual} | {error} |"
                )

        # Transcript log
        if r.transcript_log:
            lines += ["", "## Transcript Log", ""]
            for entry in r.transcript_log[:50]:  # cap at 50 lines
                lines.append(f"- {entry}")

        return "\n".join(lines)

    def save(
        self, reports_dir: Path | None = None
    ) -> tuple[Path, Path]:
        """Save JSON and Markdown report. Returns (json_path, md_path)."""
        directory = reports_dir or _REPORTS_DIR
        suite_dir = directory / self._result.suite_id
        suite_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.fromtimestamp(
            self._result.started_at or 0, tz=timezone.utc
        ).strftime("%Y%m%d-%H%M%S")
        run_id = self._result.run_id

        json_path = suite_dir / f"run-{run_id}-{ts}.json"
        md_path = suite_dir / f"run-{run_id}-{ts}.md"

        json_path.write_text(self.as_json(), encoding="utf-8")
        md_path.write_text(self.as_markdown(), encoding="utf-8")

        return json_path, md_path
