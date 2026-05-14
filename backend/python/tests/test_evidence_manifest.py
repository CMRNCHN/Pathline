import os
import json
import shutil
from pathlib import Path
from ivr_assessor.testing.evidence_manifest import EvidenceManifest, TEST_RUNS_DIR

def test_evidence_manifest_generation():
    test_id = "test-123"
    session_id = "session-456"
    manifest = EvidenceManifest(test_id, session_id)
    
    result = {"outcome": "PASSED"}
    summary = {"events_count": 10, "states_discovered": 5}
    
    manifest_path = manifest.generate(result, summary)
    
    assert os.path.exists(manifest_path)
    with open(manifest_path, "r") as f:
        data = json.load(f)
        
    assert data["test_id"] == test_id
    assert data["session_id"] == session_id
    assert data["result"] == result
    assert data["summary"] == summary
    assert "artifacts" in data
    assert data["artifacts"]["replay_session_id"] == session_id

    # Cleanup
    shutil.rmtree(TEST_RUNS_DIR)

def test_evidence_manifest_paths():
    test_id = "test-path"
    session_id = "sess-path"
    manifest = EvidenceManifest(test_id, session_id)
    
    # Check if directory structure is correct
    expected_dir = TEST_RUNS_DIR / manifest.date_str / test_id
    assert manifest.manifest_dir == expected_dir
    assert manifest.manifest_path == expected_dir / "manifest.json"

def test_evidence_manifest_listing():
    test_id = "test-list"
    session_id = "sess-list"
    manifest = EvidenceManifest(test_id, session_id)
    manifest.generate({"outcome": "PASSED"}, {"events_count": 1})
    
    tests = EvidenceManifest.list_all_tests()
    assert len(tests) >= 1
    found = any(t["test_id"] == test_id for t in tests)
    assert found
    
    latest = EvidenceManifest.get_latest_manifest(test_id)
    assert latest["test_id"] == test_id

    # Cleanup
    shutil.rmtree(TEST_RUNS_DIR)
