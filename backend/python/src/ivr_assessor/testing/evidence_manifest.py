import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..backend.ui.ui_state import EVENTS_DIR, REPLAYS_DIR, SNAPSHOTS_DIR, RECORDINGS_DIR, TEST_RUNS_DIR

class EvidenceManifest:
    def __init__(self, test_id: str, session_id: str):
        self.test_id = test_id
        self.session_id = session_id
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        self.manifest_dir = TEST_RUNS_DIR / self.date_str / self.test_id
        self.manifest_path = self.manifest_dir / "manifest.json"

    def generate(self, result: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """
        Generates a JSON manifest linking all evidence for a telecom test.
        """
        os.makedirs(self.manifest_dir, exist_ok=True)

        # Reference existing artifact paths instead of duplicating
        event_log_path = EVENTS_DIR / self.date_str / f"session_{self.session_id}.jsonl"
        snapshot_pattern = SNAPSHOTS_DIR / f"snapshot_{self.session_id}_*.json"
        
        # We don't know the exact recording name format yet, but we'll reference the dir
        # or a specific file if we can determine it from session_id.
        recording_path = RECORDINGS_DIR / f"{self.session_id}.wav" # Assumption

        manifest = {
            "test_id": self.test_id,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "summary": summary,
            "artifacts": {
                "event_log": str(event_log_path) if event_log_path.exists() else None,
                "replay_session_id": self.session_id,
                "snapshots_dir": str(SNAPSHOTS_DIR),
                "recording": str(recording_path) if recording_path.exists() else None,
                "manifest_dir": str(self.manifest_dir)
            }
        }

        with open(self.manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return str(self.manifest_path)

    @classmethod
    def get_latest_manifest(cls, test_id: str) -> Optional[dict]:
        if not TEST_RUNS_DIR.exists():
            return None
            
        # Search through date directories, newest first
        dates = sorted([d.name for d in TEST_RUNS_DIR.iterdir() if d.is_dir()], reverse=True)
        for date_str in dates:
            test_dir = TEST_RUNS_DIR / date_str / test_id
            manifest_path = test_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r") as f:
                        return json.load(f)
                except Exception:
                    continue
        return None

    @classmethod
    def list_all_tests(cls) -> list:
        tests = []
        if not TEST_RUNS_DIR.exists():
            return []
            
        dates = sorted([d.name for d in TEST_RUNS_DIR.iterdir() if d.is_dir()], reverse=True)
        seen_test_ids = set()
        
        for date_str in dates:
            date_dir = TEST_RUNS_DIR / date_str
            for test_dir in date_dir.iterdir():
                if test_dir.is_dir():
                    test_id = test_dir.name
                    if test_id in seen_test_ids:
                        continue
                        
                    manifest_path = test_dir / "manifest.json"
                    if manifest_path.exists():
                        try:
                            with open(manifest_path, "r") as f:
                                data = json.load(f)
                                tests.append({
                                    "test_id": test_id,
                                    "name": data.get("name", test_id),
                                    "outcome": data.get("result", {}).get("outcome"),
                                    "date": date_str,
                                    "started_at": data.get("result", {}).get("started_at")
                                })
                                seen_test_ids.add(test_id)
                        except Exception:
                            continue
        return tests
