import threading
import uuid
from typing import Callable
from analyst.telecom.evidence_manifest import EvidenceManifest
from analyst.telecom.evidence_exporter import EvidenceExporter
from analyst.backend.ui.ui_state import STATE, EVIDENCE_BUNDLES_DIR
from analyst.telecom.telecom_test_plan import TelecomTestPlan
from analyst.telecom.telecom_test_runner import TelecomTestRunner

# Global state for active telecom test
_active_runner: TelecomTestRunner | None = None
_runner_lock = threading.Lock()

def get_telecom_tests() -> dict:
    """Returns a list of available telecom test plans."""
    return {"tests": EvidenceManifest.list_all_tests()}

def handle_run_telecom_test(data: dict, session_thread_fn: Callable) -> dict:
    """Starts a controlled telecom validation test."""
    global _active_runner
    
    if not data.get("max_duration_seconds"):
        raise ValueError("Missing max_duration_seconds")
    if not data.get("target_number_ref"):
        raise ValueError("Missing target_number_ref")
    
    test_id = data.get("test_id", str(uuid.uuid4()))
    
    plan = TelecomTestPlan(
        test_id=test_id,
        name=data.get("name", f"Test {test_id[:8]}"),
        target_label=data.get("target_label", "Default Target"),
        target_number_ref=data["target_number_ref"],
        max_duration_seconds=int(data["max_duration_seconds"]),
        max_depth=int(data.get("max_depth", 10)),
        max_dtmf_actions=int(data.get("max_dtmf_actions", 20)),
        allow_speech_injection=bool(data.get("allow_speech_injection", False)),
        allow_human_transfer=bool(data.get("allow_human_transfer", False)),
        recording_required=bool(data.get("recording_required", True)),
        transcript_required=bool(data.get("transcript_required", True)),
        stop_on_transfer=bool(data.get("stop_on_transfer", True)),
        stop_on_low_confidence=bool(data.get("stop_on_low_confidence", True)),
        expected_initial_prompt=data.get("expected_initial_prompt"),
        notes=data.get("notes")
    )

    with _runner_lock:
        if _active_runner and STATE.is_running:
            return {"status": "error", "message": "Another test or session is already running"}
        
        _active_runner = TelecomTestRunner(plan)
        
    # Start the test in a separate thread
    threading.Thread(
        target=_active_runner.run,
        args=(session_thread_fn, data),
        daemon=True
    ).start()

    return {"status": "started", "test_id": test_id}

def get_telecom_test_status(test_id: str) -> dict:
    """Returns the status and results of a specific telecom test."""
    global _active_runner
    with _runner_lock:
        if _active_runner and _active_runner.plan.test_id == test_id:
            return {
                "test_id": test_id,
                "status": "running" if STATE.is_running else "completed",
                "result": _active_runner.result.to_dict() if _active_runner.result else None
            }
    return {"status": "not_found"}

def handle_abort_telecom_test(test_id: str) -> dict:
    """Aborts a running telecom test."""
    global _active_runner
    with _runner_lock:
        if _active_runner and _active_runner.plan.test_id == test_id:
            _active_runner.abort()
            return {"status": "aborting"}
    return {"status": "not_found"}

def get_telecom_test_evidence(test_id: str) -> dict:
    """Returns the evidence manifest for a telecom test."""
    manifest = EvidenceManifest.get_latest_manifest(test_id)
    return {"test_id": test_id, "evidence": manifest}

def handle_export_evidence_bundle(data: dict) -> dict:
    """Exports an evidence bundle for a session/test."""
    session_id = data.get("session_id")
    test_id = data.get("test_id")
    if not session_id:
        raise ValueError("Missing session_id")
    
    exporter = EvidenceExporter()
    bundle = exporter.export(
        session_id=session_id, 
        test_id=test_id, 
        copy_recording=data.get("copy_recording", False)
    )
    
    return {
        "status": "success", 
        "bundle_id": bundle.metadata.bundle_id,
        "root_path": str(bundle.root_path)
    }

def get_evidence_bundles() -> dict:
    """Lists all exported evidence bundles."""
    bundles = []
    if not EVIDENCE_BUNDLES_DIR.exists():
        return {"bundles": []}
    
    for date_dir in sorted(EVIDENCE_BUNDLES_DIR.iterdir(), reverse=True):
        if date_dir.is_dir():
            for bundle_dir in sorted(date_dir.iterdir(), reverse=True):
                 if bundle_dir.is_dir():
                    manifest_path = bundle_dir / "manifest.json"
                    if manifest_path.exists():
                        try:
                            import json
                            with open(manifest_path, "r") as f:
                                bundles.append(json.load(f))
                        except Exception:
                            continue
    return {"bundles": bundles}

def get_bundle_manifest(bundle_id: str) -> dict:
    """Returns the manifest for a specific bundle."""
    # Search for bundle_id in date dirs
    for date_dir in EVIDENCE_BUNDLES_DIR.iterdir():
        if date_dir.is_dir():
            bundle_dir = date_dir / bundle_id
            manifest_path = bundle_dir / "manifest.json"
            if manifest_path.exists():
                import json
                with open(manifest_path, "r") as f:
                    return json.load(f)
    return {"status": "not_found"}

def get_bundle_report(bundle_id: str) -> dict:
    """Returns the report data for a specific bundle."""
    for date_dir in EVIDENCE_BUNDLES_DIR.iterdir():
        if date_dir.is_dir():
            bundle_dir = date_dir / bundle_id
            report_path = bundle_dir / "report.json"
            if report_path.exists():
                import json
                with open(report_path, "r") as f:
                    return json.load(f)
    return {"status": "not_found"}