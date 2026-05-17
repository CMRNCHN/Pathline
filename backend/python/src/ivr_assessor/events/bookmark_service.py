import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from ..backend.ui.ui_state import ANNOTATIONS_DIR
from .replay_bookmark import ReplayBookmark

logger = logging.getLogger(__name__)

class BookmarkService:
    def __init__(self, base_dir: Path = ANNOTATIONS_DIR):
        self.base_dir = base_dir

    def _get_storage_path(self, session_id: str, created_at: str) -> Path:
        # Storage: ~/.ivr_assessor/review_annotations/YYYY-MM-DD/session__bookmarks.jsonl
        date_str = created_at.split('T')[0] if 'T' in created_at else datetime.now().strftime('%Y-%m-%d')
        directory = self.base_dir / date_str
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{session_id}__bookmarks.jsonl"

    def add_bookmark(self, bookmark: ReplayBookmark) -> None:
        path = self._get_storage_path(bookmark.session_id, bookmark.created_at)
        with open(path, "a") as f:
            f.write(json.dumps(bookmark.to_dict()) + "\n")

    def get_bookmarks(self, session_id: str) -> List[ReplayBookmark]:
        bookmarks = []
        # We need to find the file for this session. Since it's partitioned by date, 
        # we might need to search or know which date. 
        # For simplicity in this track, we can search all subdirectories if needed, 
        # or assume the caller might know the date. 
        # But if we only have session_id, we should probably search.
        
        if not self.base_dir.exists():
            return []

        for date_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                path = date_dir / f"{session_id}__bookmarks.jsonl"
                if path.exists():
                    with open(path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                bookmarks.append(ReplayBookmark.from_dict(json.loads(line)))
                            except (json.JSONDecodeError, KeyError, ValueError) as e:
                                logger.error(f"Malformed bookmark line in {path}: {e}")
                                continue
        return bookmarks

bookmark_service = BookmarkService()
