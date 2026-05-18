import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from analyst.backend.ui.ui_state import ANNOTATIONS_DIR
from runtime.events.replay_annotation import ReplayAnnotation

logger = logging.getLogger(__name__)

class AnnotationService:
    def __init__(self, base_dir: Path = ANNOTATIONS_DIR):
        self.base_dir = base_dir

    def _get_storage_path(self, session_id: str, created_at: str) -> Path:
        date_str = created_at.split('T')[0] if 'T' in created_at else datetime.now().strftime('%Y-%m-%d')
        directory = self.base_dir / date_str
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{session_id}__annotations.jsonl"

    def add_annotation(self, annotation: ReplayAnnotation) -> None:
        path = self._get_storage_path(annotation.session_id, annotation.created_at)
        with open(path, "a") as f:
            f.write(json.dumps(annotation.to_dict()) + "\n")

    def get_annotations(self, session_id: str) -> List[ReplayAnnotation]:
        annotations: Dict[str, ReplayAnnotation] = {}
        
        if not self.base_dir.exists():
            return []

        # Find all annotation files for this session across all date directories
        # and process them in order to handle revisions.
        all_lines = []
        for date_dir in sorted(self.base_dir.iterdir()):
            if date_dir.is_dir():
                path = date_dir / f"{session_id}__annotations.jsonl"
                if path.exists():
                    with open(path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                all_lines.append(line)
        
        for line in all_lines:
            try:
                ann = ReplayAnnotation.from_dict(json.loads(line))
                # If this is a revision, it replaces the original in our current view.
                # Note: original is still in the file (append-only).
                annotations[ann.annotation_id] = ann
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Malformed annotation line: {e}")
                continue
                
        # To strictly handle revisions as new IDs pointing to old ones:
        # The requirement says "editing is represented as a new revision"
        # and "annotation_id" is unique.
        # If revision_of is set, we should probably only show the latest version.
        
        latest_annotations: Dict[str, ReplayAnnotation] = {}
        # Map of original_id -> latest_annotation
        for ann in annotations.values():
            root_id = ann.revision_of if ann.revision_of else ann.annotation_id
            # This is a bit simplistic if there are multiple levels of revision, 
            # but usually it's one or two. Let's trace back to root.
            # For this track, we'll assume revision_of points to the very first ID.
            if root_id not in latest_annotations or ann.created_at > latest_annotations[root_id].created_at:
                latest_annotations[root_id] = ann
                
        return sorted(latest_annotations.values(), key=lambda x: x.created_at)

annotation_service = AnnotationService()