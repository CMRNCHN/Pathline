from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CallMode(str, Enum):
    CLIENT_MEDIATED = "client_mediated"
    SERVER_MEDIATED = "server_mediated"


class CallStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConsentRecord(BaseModel):
    accepted: bool
    timestamp: str
    terms_version: str = "1.0"


class TokenRequest(BaseModel):
    user_id: str
    call_mode: CallMode
    consent: ConsentRecord


class TokenResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"


class EncryptedSecrets(BaseModel):
    """Client-side encrypted secrets blob — server never sees plaintext."""
    ciphertext: str
    nonce: str
    key_id: str


class CallRequest(BaseModel):
    target_number: str = Field(description="Destination number (E.164)")
    encrypted_secrets: EncryptedSecrets | None = None
    call_mode: CallMode = CallMode.CLIENT_MEDIATED
    metadata: dict[str, Any] = Field(default_factory=dict)


class CallSession(BaseModel):
    session_id: str
    status: CallStatus
    call_mode: CallMode
    hashed_session_id: str
    created_at: str
    updated_at: str
    did_assigned: str | None = None
    provider: str | None = None


class DIDRecord(BaseModel):
    number: str
    provider: str
    status: str
    last_used_at: str | None = None
    cooldown_until: str | None = None


class StatusReport(BaseModel):
    session_id: str
    status: CallStatus
    encrypted_result: str | None = None
    transcript_hash: str | None = None


class NotificationPayload(BaseModel):
    session_id: str
    event: str
    message: str
    severity: str = "info"
