from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from runtime.telemetry.logging_config import configure_logging

logger = logging.getLogger(__name__)

_BOOTSTRAPPED = False
_BOOTSTRAP_METADATA: dict[str, Any] = {}
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_ENV_PATH = _REPO_ROOT / ".env"


def _parse_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        parsed[key] = value
    return parsed


def load_runtime_env(
    env_path: Path | None = None,
    *,
    override: bool = False,
) -> dict[str, Any]:
    path = env_path or _DEFAULT_ENV_PATH
    parsed = _parse_env_file(path) if path.exists() else {}

    method = "missing"
    loaded_keys = 0

    if path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(path, override=override)
            method = "python-dotenv"
            loaded_keys = sum(1 for key in parsed if os.getenv(key))
        except ModuleNotFoundError:
            method = "manual-fallback"
            for key, value in parsed.items():
                if override or key not in os.environ:
                    os.environ[key] = value
                    loaded_keys += 1

    return {
        "env_path": str(path),
        "env_exists": path.exists(),
        "env_method": method,
        "env_keys_loaded": loaded_keys,
        "env_keys_present": len(parsed),
        "override": override,
    }


def bootstrap_runtime(*, force: bool = False) -> dict[str, Any]:
    global _BOOTSTRAPPED, _BOOTSTRAP_METADATA

    if _BOOTSTRAPPED and not force:
        return dict(_BOOTSTRAP_METADATA)

    metadata = load_runtime_env()
    configure_logging()
    metadata["log_level"] = os.getenv("LOG_LEVEL", "INFO")
    _BOOTSTRAP_METADATA = metadata
    _BOOTSTRAPPED = True

    logger.info(
        "Runtime bootstrap ready: env=%s method=%s keys_loaded=%d log_level=%s",
        metadata["env_path"],
        metadata["env_method"],
        metadata["env_keys_loaded"],
        metadata["log_level"],
    )
    return dict(_BOOTSTRAP_METADATA)