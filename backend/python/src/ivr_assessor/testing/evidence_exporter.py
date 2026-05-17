import json
import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..backend.ui.ui_state import (
    EVIDENCE_BUNDLES_DIR,
    EVENTS_DIR,
    REPLAYS_DIR,
    SNAPSHOTS_DIR,
    RECORDINGS_DIR,
    WAVEFORMS_DIR,
    ANNOTATIONS_DIR
)
from .evidence_bundle import EvidenceBundle, EvidenceBundleMetadata
from .integrity_manifest import IntegrityManifest
from .qa_scorer import QAScorer
from .failure_classifier import FailureClassifier
from .benchmark_overlay import BenchmarkOverlay
from .report_generator import ReportGenerator

class EvidenceExporter:
    def __init__(self, output_base_dir: Path = EVIDENCE_BUNDLES_DIR):
        self.output_base_dir = output_base_dir
        self.qa_scorer = QAScorer()
        self.failure_classifier = FailureClassifier()
        self.benchmark_overlay = BenchmarkOverlay()

    def export(self, 
               session_id: str, 
               test_id: Optional[str] = None, 
               copy_recording: bool = False,
               bundle_id: Optional[str] = None) -> EvidenceBundle:
        
        if not bundle_id:
            bundle_id = f"bundle_{session_id}_{datetime.now().strftime('%H%M%S')}"
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        bundle_path = self.output_base_dir / date_str / bundle_id
        bundle_path.mkdir(parents=True, exist_ok=True)

        exported_files = []

        # 0. Load Events (needed for scoring and reports)
        events = self._load_events(session_id)
        
        # 1. Event Log
        event_log = self._find_event_log(session_id)
        if event_log:
            exported_files.append(self._copy_or_link(event_log, bundle_path / "events.jsonl"))

        # 2. Replay Metadata
        replay_meta = REPLAYS_DIR / f"replay_{session_id}.json"
        if replay_meta.exists():
            exported_files.append(self._copy_or_link(replay_meta, bundle_path / "replay.json"))

        # 3. Waveform Metadata
        waveform_meta = WAVEFORMS_DIR / f"waveform_{session_id}.json"
        if waveform_meta.exists():
            exported_files.append(self._copy_or_link(waveform_meta, bundle_path / "waveform.json"))

        # 4. Snapshots
        snapshots = list(SNAPSHOTS_DIR.glob(f"snapshot_{session_id}_*.json"))
        if snapshots:
            snapshots_dir = bundle_path / "snapshots"
            snapshots_dir.mkdir(exist_ok=True)
            for s in snapshots:
                exported_files.append(self._copy_or_link(s, snapshots_dir / s.name))

        # 5. Recording
        recording = RECORDINGS_DIR / f"{session_id}.wav"
        if recording.exists():
            if copy_recording:
                exported_files.append(self._copy_or_link(recording, bundle_path / "recording.wav", force_copy=True))
            else:
                # Create a reference file
                ref_file = bundle_path / "recording_reference.json"
                with open(ref_file, "w") as f:
                    json.dump({"original_path": str(recording)}, f)
                exported_files.append(ref_file)

        # 6. Annotations
        annotation_file = ANNOTATIONS_DIR / f"annotations_{session_id}.json"
        if annotation_file.exists():
            exported_files.append(self._copy_or_link(annotation_file, bundle_path / "annotations.json"))

        # 7. QA, Classification, Benchmarks
        # We need telecom_result if available
        telecom_result = self._load_telecom_result(test_id)
        
        qa_score = self.qa_scorer.score_session(events, telecom_result)
        failure_info = self.failure_classifier.classify(events, telecom_result)
        benchmarks = self.benchmark_overlay.summarize(events, telecom_result)

        # 8. Integrity Manifest
        integrity = IntegrityManifest(bundle_id)
        for f in exported_files:
            integrity.add_file(f, bundle_path)
        integrity_hash = integrity.generate(bundle_path / "integrity.json")
        exported_files.append(bundle_path / "integrity.json")

        # 9. Report Generation
        metadata_dict = {
            "bundle_id": bundle_id,
            "session_id": session_id,
            "test_id": test_id,
            "created_at": datetime.now().isoformat()
        }
        report_gen = ReportGenerator(bundle_path)
        report_files = report_gen.generate(metadata_dict, qa_score, failure_info, benchmarks, integrity_hash)
        exported_files.append(Path(report_files["json"]))
        exported_files.append(Path(report_files["md"]))

        # 10. Final Bundle Manifest
        manifest = {
            "bundle_id": bundle_id,
            "session_id": session_id,
            "test_id": test_id,
            "exported_at": datetime.now().isoformat(),
            "files": [str(f.relative_to(bundle_path)) for f in exported_files],
            "integrity_hash": integrity_hash
        }
        manifest_path = bundle_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        exported_files.append(manifest_path)

        metadata = EvidenceBundleMetadata(
            bundle_id=bundle_id,
            session_id=session_id,
            test_id=test_id,
            file_count=len(exported_files),
            size_bytes=sum(os.path.getsize(f) for f in exported_files if f.is_file()),
            sha256=integrity_hash
        )

        return EvidenceBundle(metadata=metadata, root_path=bundle_path, files=exported_files)

    def _load_events(self, session_id: str) -> List[Dict[str, Any]]:
        log_path = self._find_event_log(session_id)
        events = []
        if log_path:
            with open(log_path, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return events

    def _load_telecom_result(self, test_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not test_id:
            return None
        from .evidence_manifest import EvidenceManifest
        manifest = EvidenceManifest.get_latest_manifest(test_id)
        if manifest:
            return manifest.get("result")
        return None

    def _find_event_log(self, session_id: str) -> Optional[Path]:
        pattern = f"session_{session_id}.jsonl"
        if not EVENTS_DIR.exists():
            return None
        for date_dir in EVENTS_DIR.iterdir():
            if date_dir.is_dir():
                potential = date_dir / pattern
                if potential.exists():
                    return potential
        return None

    def _copy_or_link(self, src: Path, dst: Path, force_copy: bool = False) -> Path:
        if force_copy or True: # Force copy for portability as requested for bundles
            shutil.copy2(src, dst)
        return dst
