import os
from pathlib import Path

# Base directory for all Pathline data
BASE_DIR = Path(os.path.expanduser("~/.ivr_assessor"))

# Subdirectories
SUITES_DIR = BASE_DIR / "suites"
RUN_SUITES_DIR = BASE_DIR / "run_suites"
REPORTS_DIR = BASE_DIR / "reports"
RUN_SUITE_REPORTS_DIR = BASE_DIR / "run_suite_reports"
RECORDINGS_DIR = BASE_DIR / "recordings"
REPLAYS_DIR = BASE_DIR / "replays"
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
BENCHMARKS_DIR = BASE_DIR / "benchmarks"
EVENTS_DIR = BASE_DIR / "events"
TEST_RUNS_DIR = BASE_DIR / "test_runs"
ANNOTATIONS_DIR = BASE_DIR / "annotations"

# Ensure directories exist
for path in [
    BASE_DIR, SUITES_DIR, RUN_SUITES_DIR, REPORTS_DIR,
    RUN_SUITE_REPORTS_DIR, RECORDINGS_DIR, REPLAYS_DIR,
    SNAPSHOTS_DIR, BENCHMARKS_DIR, EVENTS_DIR, TEST_RUNS_DIR,
    ANNOTATIONS_DIR
]:
    path.mkdir(parents=True, exist_ok=True)

# Operational constants
SNAPSHOT_INTERVAL = 100
