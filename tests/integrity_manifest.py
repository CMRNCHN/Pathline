import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class IntegrityManifest:
    def __init__(self, bundle_id: str):
        self.bundle_id = bundle_id
        self.created_at = datetime.now().isoformat()
        self.files: List[Dict[str, Any]] = []

    def add_file(self, file_path: Path, relative_to: Path):
        sha256 = self._calculate_sha256(file_path)
        self.files.append({
            "relative_path": str(file_path.relative_to(relative_to)),
            "sha256": sha256,
            "size_bytes": file_path.stat().st_size
        })

    def _calculate_sha256(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def generate(self, output_path: Path) -> str:
        manifest = {
            "bundle_id": self.bundle_id,
            "created_at": self.created_at,
            "file_count": len(self.files),
            "total_size_bytes": sum(f["size_bytes"] for f in self.files),
            "files": self.files
        }
        
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)
            
        return self._calculate_sha256(output_path)