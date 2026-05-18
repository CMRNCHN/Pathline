import os
import json
from tests.evidence_exporter import EvidenceExporter

def test_evidence_exporter_basic(tmp_path):
    # Setup mock environment
    os.environ["IVR_EVIDENCE_BUNDLES_DIR"] = str(tmp_path / "bundles")
    exporter = EvidenceExporter(output_base_dir=tmp_path / "bundles")
    
    session_id = "test_session_123"
    
    # Create mock event log
    events_dir = tmp_path / "events" / "2026-05-14"
    events_dir.mkdir(parents=True)
    event_log = events_dir / f"session_{session_id}.jsonl"
    with open(event_log, "w") as f:
        f.write(json.dumps({"kind": "recording_started", "t_ms": 0}) + "\n")
        f.write(json.dumps({"kind": "speech_detected", "payload": {"confidence": 0.9}, "t_ms": 1000}) + "\n")
        f.write(json.dumps({"kind": "dtmf_sent", "payload": {"digits": "1"}, "t_ms": 2000}) + "\n")

    # Monkeypatch EVENTS_DIR for this test
    import tests.evidence_exporter as ee
    old_events_dir = ee.EVENTS_DIR
    ee.EVENTS_DIR = tmp_path / "events"
    
    try:
        bundle = exporter.export(session_id=session_id)
        
        assert bundle.exists()
        assert (bundle.root_path / "events.jsonl").exists()
        assert (bundle.root_path / "manifest.json").exists()
        assert (bundle.root_path / "report.json").exists()
        assert (bundle.root_path / "report.md").exists()
        assert (bundle.root_path / "integrity.json").exists()
        
        # Check integrity
        with open(bundle.root_path / "integrity.json", "r") as f:
            integrity = json.load(f)
            assert integrity["bundle_id"] == bundle.metadata.bundle_id
            assert len(integrity["files"]) > 0
            
        # Check report
        with open(bundle.root_path / "report.json", "r") as f:
            report = json.load(f)
            assert report["qa_score"]["session_score"] > 0
            assert report["benchmarks"]["prompt_count"] >= 0
            
    finally:
        ee.EVENTS_DIR = old_events_dir

def test_secret_safety(tmp_path):
    exporter = EvidenceExporter(output_base_dir=tmp_path / "bundles")
    session_id = "secret_session"
    
    # Create bundle directory
    bundle_path = tmp_path / "bundles" / "2026-05-14" / "secret_bundle"
    bundle_path.mkdir(parents=True)
    
    # Mock .env file that SHOULD NOT be included
    env_file = tmp_path / ".env"
    env_file.write_text("TWILIO_AUTH_TOKEN=supersecret")
    
    # The exporter doesn't have a way to include arbitrary files, but let's 
    # ensure our file finding logic doesn't pick up sensitive dirs.
    # We'll just verify that the manifest doesn't contain any secret-looking paths.
    
    bundle = exporter.export(session_id=session_id, bundle_id="secret_bundle")
    
    with open(bundle.root_path / "manifest.json", "r") as f:
        manifest = json.load(f)
        for file_path in manifest["files"]:
            assert ".env" not in file_path
            assert "credentials" not in file_path.lower()