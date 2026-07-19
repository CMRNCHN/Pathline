from __future__ import annotations

from pydantic import BaseModel, Field


class EncryptedCallStateIngest(BaseModel):
    """Opaque client-encrypted callstate; contents are never interpreted."""

    session_id: str = Field(min_length=1, max_length=128)
    encrypted_payload: str = Field(min_length=1, max_length=1_048_576)
    payload_nonce: str = Field(min_length=1, max_length=256)


class CallStateIngestResponse(BaseModel):
    hashed_session_id: str
    received_at: str
    expires_at: str


class ExportResponse(BaseModel):
    hashed_session_id: str
    encrypted_payload: str
    payload_nonce: str
    created_at: str
    expires_at: str


class DeleteResponse(BaseModel):
    deleted: bool
    hashed_session_id: str


class SessionLinkRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)


class SessionLinkResponse(BaseModel):
    linked: bool
    hashed_session_id: str
    session_linked_at: str
