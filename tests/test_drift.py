import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def test_legacy_drift_detection():
    """
    Scans the project for legacy references and forbidden patterns.
    - No IVRSuite references (case-insensitive)
    - No forbidden directories (e.g., old legacy folders if any)
    """
    forbidden_terms = ["IVRSuite"]
    # We allow these specific files/dirs as they are part of the new architecture or docs
    allowed_paths = [
        "docs/legacy",
        "docs/CHANGELOG.md",
        ".ai/TASKS/COMPLETED",
        "tests/test_architecture.py",
        "tests/test_drift.py",
        "scripts/drift_check.py"
    ]
    
    violations = []
    
    # Files to ignore (binaries, etc)
    ignore_extensions = [".png", ".jpg", ".jpeg", ".wav", ".mp3", ".pyc", ".db", ".iml"]
    ignore_dirs = [".git", ".venv", "__pycache__", "node_modules", "pathline.egg-info", "tmp", ".claude"]

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Filter directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(PROJECT_ROOT)
            
            if any(str(rel_path).startswith(ap) for ap in allowed_paths):
                continue
                
            if any(file.endswith(ext) for ext in ignore_extensions):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for term in forbidden_terms:
                        if term in content:
                            violations.append(f"VIOLATION in {rel_path}: Found legacy term '{term}'")
            except Exception:
                # Skip files that can't be read
                pass

    if violations:
        pytest.fail("\n".join(violations))

def test_topology_drift():
    """
    Checks for presence of forbidden legacy directories.
    """
    forbidden_dirs = ["IVRSuite", "legacy_backend", "old_tests"]
    
    violations = []
    for d in forbidden_dirs:
        path = PROJECT_ROOT / d
        if path.exists():
            violations.append(f"VIOLATION: Forbidden legacy directory exists: {d}")
            
    if violations:
        pytest.fail("\n".join(violations))

if __name__ == "__main__":
    try:
        test_legacy_drift_detection()
        test_topology_drift()
        print("No architectural drift detected!")
    except Exception as e:
        print(e)
