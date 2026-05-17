from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

@dataclass
class EvidenceBundleMetadata:
    bundle_id: str
    session_id: str
    test_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    file_count: int = 0
    size_bytes: int = 0
    sha256: Optional[str] = None

@dataclass
class EvidenceBundle:
    metadata: EvidenceBundleMetadata
    root_path: Path
    files: List[Path] = field(default_factory=list)

    def exists(self) -> bool:
        return self.root_path.exists()
