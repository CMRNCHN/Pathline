"""
replay/anomaly_detection.py — Stub owned by Agent 3.

Exports ``detect_anomalies`` and ``generate_next_steps`` as no-ops until
Agent 3 wires in the real implementation.  ``replay/inspection_service.py``
imports from here and falls back to its own lambda stubs if this import fails,
so the two are compatible at every stage of development.
"""

from __future__ import annotations

from replay.inspection_models import Anomaly, NextStep, ReplayInspectionReport


def detect_anomalies(report: ReplayInspectionReport) -> list[Anomaly]:
    """Return detected anomalies for *report*. Stub: always returns []."""
    return []


def generate_next_steps(report: ReplayInspectionReport) -> list[NextStep]:
    """Return recommended next steps for *report*. Stub: always returns []."""
    return []


__all__ = ["detect_anomalies", "generate_next_steps"]
