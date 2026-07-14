from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from pathline_shared.crypto import decrypt_payload, encrypt_payload
from pathline_shared.logging_config import configure_logging, get_logger

configure_logging("kms")
logger = get_logger("kms")

app = FastAPI(title="Pathline KMS (Dev Mock)", version="0.1.0")


class Settings(BaseSettings):
    kms_master_key: str = "dev-master-key-change-me-32bytes!!"
    key_release_ttl_seconds: int = 60

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
_audit_log: list[dict] = []
_active_keys: dict[str, dict] = {}


class KeyReleaseRequest(BaseModel):
    purpose: str
    requester: str


class KeyReleaseResponse(BaseModel):
    key_id: str
    key_b64: str
    expires_at: str


class EncryptRequest(BaseModel):
    plaintext_b64: str
    key_id: str | None = None


class DecryptRequest(BaseModel):
    ciphertext_b64: str
    key_id: str


class AuditEntry(BaseModel):
    action: str
    resource: str
    requester: str | None = None


def _master_key_bytes() -> bytes:
    key = settings.kms_master_key.encode()
    return key[:32].ljust(32, b"\0")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "kms", "mode": "dev-mock"}


@app.post("/v1/keys/release", response_model=KeyReleaseResponse)
async def release_key(request: KeyReleaseRequest):
    """Release a short-lived decryption key — simulates HSM key release."""
    key_id = str(uuid.uuid4())
    key_bytes = os.urandom(32)
    expires = datetime.now(UTC) + timedelta(seconds=settings.key_release_ttl_seconds)
    _active_keys[key_id] = {"key": key_bytes, "expires": expires, "purpose": request.purpose}

    import base64
    _audit_log.append({
        "action": "key_release",
        "purpose": request.purpose,
        "requester": request.requester,
        "key_id": key_id,
        "timestamp": datetime.now(UTC).isoformat(),
    })
    logger.info("key_released", key_id=key_id[:8] + "...", purpose=request.purpose)
    return KeyReleaseResponse(
        key_id=key_id,
        key_b64=base64.b64encode(key_bytes).decode(),
        expires_at=expires.isoformat(),
    )


@app.post("/v1/audit")
async def audit(entry: AuditEntry):
    _audit_log.append({**entry.model_dump(), "timestamp": datetime.now(UTC).isoformat()})
    logger.info("audit", action=entry.action, resource=entry.resource)
    return {"logged": True}


@app.get("/v1/audit")
async def get_audit(limit: int = 50):
    return _audit_log[-limit:]
