from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from pathline_shared.logging_config import get_logger
from pathline_shared.models import TokenRequest, TokenResponse

from .auth import artifact_hash, mint_token, owner_hash, verify_token
from .database import get_db
from .middleware import enforce_authenticated_rate_limit, enforce_token_rate_limit
from .models import CallStateRecord, ConsentAudit, IdempotencyRecord, NotificationRecord, RevokedToken
from .schemas import (
    CallStateIngestResponse,
    DeleteResponse,
    EncryptedCallStateIngest,
    ExportResponse,
    SessionLinkRequest,
    SessionLinkResponse,
)

router = APIRouter()
logger = get_logger("api")
AuthPayload = Annotated[dict[str, Any], Depends(verify_token)]
Database = Annotated[AsyncSession, Depends(get_db)]


def parse_consent_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid consent timestamp") from exc
    if parsed.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Consent timestamp must include a timezone")
    return parsed.astimezone(UTC)


def validate_token_request(body: TokenRequest) -> None:
    if not 1 <= len(body.user_id) <= 128:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "user_id must be 1-128 characters")
    if not 1 <= len(body.consent.terms_version) <= 32:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "terms_version must be 1-32 characters")


async def require_owned_consent(
    db: AsyncSession,
    payload: dict[str, Any],
    hashed_session_id: str,
    *,
    link_if_empty: bool,
    now: datetime,
) -> ConsentAudit:
    consent = await db.get(ConsentAudit, payload["jti"])
    if not consent or consent.owner_hash != payload["owner_hash"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Consent is not valid for this owner")
    if consent.hashed_session_id and consent.hashed_session_id != hashed_session_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Token consent is already linked to another session")
    if link_if_empty and not consent.hashed_session_id:
        consent.hashed_session_id = hashed_session_id
        consent.session_linked_at = now
    return consent


async def apply_authenticated_limit(request: Request, payload: dict[str, Any]) -> None:
    await enforce_authenticated_rate_limit(request, payload["owner_hash"])


@router.post("/v1/token", response_model=TokenResponse, dependencies=[Depends(enforce_token_rate_limit)])
async def create_token(body: TokenRequest, request: Request, db: Database) -> TokenResponse:
    validate_token_request(body)
    if not body.consent.accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Consent required")
    if body.call_mode.value != "client_mediated":
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Server-mediated calls are v3. Use client-mediated flow.",
        )

    consent_at = parse_consent_timestamp(body.consent.timestamp)
    now = datetime.now(UTC)
    if consent_at > now + timedelta(minutes=5) or consent_at < now - timedelta(days=1):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Consent timestamp is outside the accepted window")

    token, ttl, jti = mint_token(body.user_id, body.consent.terms_version, request)
    settings = request.app.state.settings
    owner = owner_hash(jti, settings.session_pepper)
    db.add(
        ConsentAudit(
            jti=jti,
            owner_hash=owner,
            terms_version=body.consent.terms_version,
            consent_at=consent_at,
            call_mode=body.call_mode.value,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )
    )
    await db.commit()
    logger.info("consent_recorded", owner_ref=owner[:12])
    return TokenResponse(access_token=token, expires_in=ttl)


@router.post("/v1/consent/session", response_model=SessionLinkResponse)
async def link_session_to_consent(
    body: SessionLinkRequest,
    request: Request,
    db: Database,
    payload: AuthPayload,
) -> SessionLinkResponse:
    await apply_authenticated_limit(request, payload)
    settings = request.app.state.settings
    if len(body.session_id) > settings.max_session_id_length:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "session_id is too long")
    hashed = artifact_hash(body.session_id, payload["owner_hash"], settings.session_pepper)
    now = datetime.now(UTC)
    record = await require_owned_consent(db, payload, hashed, link_if_empty=True, now=now)
    linked_at = record.session_linked_at or now
    await db.commit()
    logger.info("consent_session_linked", owner_ref=payload["owner_hash"][:12], artifact_ref=hashed[:12])
    return SessionLinkResponse(
        linked=True,
        hashed_session_id=hashed,
        session_linked_at=linked_at.isoformat(),
    )


@router.post("/v1/callstate", response_model=CallStateIngestResponse)
async def ingest_callstate(
    body: EncryptedCallStateIngest,
    request: Request,
    db: Database,
    payload: AuthPayload,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
) -> CallStateIngestResponse:
    await apply_authenticated_limit(request, payload)
    settings = request.app.state.settings
    if len(body.session_id) > settings.max_session_id_length:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "session_id is too long")
    if len(body.encrypted_payload.encode()) > settings.max_encrypted_payload_bytes:
        raise HTTPException(413, "Encrypted payload is too large")
    if len(body.payload_nonce) > settings.max_nonce_length:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "payload_nonce is too long")

    hashed = artifact_hash(body.session_id, payload["owner_hash"], settings.session_pepper)
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.retention_seconds)
    stored = json.dumps(
        {"encrypted_payload": body.encrypted_payload, "payload_nonce": body.payload_nonce},
        separators=(",", ":"),
    )
    digest = hashlib.sha256(stored.encode()).hexdigest()
    await require_owned_consent(db, payload, hashed, link_if_empty=True, now=now)

    if idempotency_key:
        replay = await db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.owner_hash == payload["owner_hash"],
                IdempotencyRecord.operation == "callstate_ingest",
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
        )
        if replay:
            if replay.request_digest != digest:
                raise HTTPException(status.HTTP_409_CONFLICT, "Idempotency key was reused with different content")
            return CallStateIngestResponse.model_validate_json(replay.response_body)

    existing = await db.get(CallStateRecord, hashed)
    create_notification = True
    if existing:
        if existing.owner_hash != payload["owner_hash"]:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No data for session")
        create_notification = existing.payload_digest != digest
        existing.encrypted_payload = stored
        existing.payload_digest = digest
        existing.updated_at = now
        existing.expires_at = expires
    else:
        db.add(
            CallStateRecord(
                hashed_id=hashed,
                owner_hash=payload["owner_hash"],
                encrypted_payload=stored,
                payload_digest=digest,
                created_at=now,
                updated_at=now,
                expires_at=expires,
            )
        )

    if create_notification:
        db.add(
            NotificationRecord(
                id=str(uuid.uuid4()),
                owner_hash=payload["owner_hash"],
                hashed_id=hashed,
                event="callstate_received",
                message="Encrypted callstate ingested",
                severity="info",
                created_at=now,
                expires_at=min(
                    expires,
                    now + timedelta(seconds=settings.notification_retention_seconds),
                ),
            )
        )

    response = CallStateIngestResponse(
        hashed_session_id=hashed,
        received_at=now.isoformat(),
        expires_at=expires.isoformat(),
    )
    if idempotency_key:
        db.add(
            IdempotencyRecord(
                id=str(uuid.uuid4()),
                owner_hash=payload["owner_hash"],
                operation="callstate_ingest",
                idempotency_key=idempotency_key,
                request_digest=digest,
                response_body=response.model_dump_json(),
                created_at=now,
                expires_at=expires,
            )
        )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if not idempotency_key:
            raise HTTPException(status.HTTP_409_CONFLICT, "Concurrent callstate update; retry request") from exc
        replay = await db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.owner_hash == payload["owner_hash"],
                IdempotencyRecord.operation == "callstate_ingest",
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
        )
        if not replay or replay.request_digest != digest:
            raise HTTPException(status.HTTP_409_CONFLICT, "Idempotency key conflict") from exc
        return CallStateIngestResponse.model_validate_json(replay.response_body)
    logger.info("callstate_ingested", artifact_ref=hashed[:12])
    return response


@router.post("/v1/status", response_model=CallStateIngestResponse, include_in_schema=False)
async def ingest_status_legacy(
    body: EncryptedCallStateIngest,
    request: Request,
    db: Database,
    payload: AuthPayload,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
) -> CallStateIngestResponse:
    return await ingest_callstate(body, request, db, payload, idempotency_key)


@router.get("/v1/callstate/{session_id}/export", response_model=ExportResponse)
async def export_callstate(session_id: str, request: Request, db: Database, payload: AuthPayload) -> ExportResponse:
    await apply_authenticated_limit(request, payload)
    settings = request.app.state.settings
    if not 1 <= len(session_id) <= settings.max_session_id_length:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid session_id")
    hashed = artifact_hash(session_id, payload["owner_hash"], settings.session_pepper)
    record = await db.get(CallStateRecord, hashed)
    if not record or record.owner_hash != payload["owner_hash"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No data for session")
    data = json.loads(record.encrypted_payload)
    return ExportResponse(
        hashed_session_id=hashed,
        encrypted_payload=data["encrypted_payload"],
        payload_nonce=data["payload_nonce"],
        created_at=record.created_at.isoformat(),
        expires_at=record.expires_at.isoformat(),
    )


@router.get("/v1/status/{session_id}/export", response_model=ExportResponse, include_in_schema=False)
async def export_status_legacy(
    session_id: str, request: Request, db: Database, payload: AuthPayload
) -> ExportResponse:
    return await export_callstate(session_id, request, db, payload)


@router.delete("/v1/callstate/{session_id}", response_model=DeleteResponse)
async def delete_callstate(session_id: str, request: Request, db: Database, payload: AuthPayload) -> DeleteResponse:
    await apply_authenticated_limit(request, payload)
    settings = request.app.state.settings
    if not 1 <= len(session_id) <= settings.max_session_id_length:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid session_id")
    hashed = artifact_hash(session_id, payload["owner_hash"], settings.session_pepper)
    record = await db.get(CallStateRecord, hashed)
    if record and record.owner_hash != payload["owner_hash"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No data for session")
    if record:
        await db.delete(record)
    await db.execute(
        delete(NotificationRecord).where(
            NotificationRecord.owner_hash == payload["owner_hash"],
            NotificationRecord.hashed_id == hashed,
        )
    )
    await db.commit()
    logger.info("callstate_deleted", artifact_ref=hashed[:12], existed=record is not None)
    return DeleteResponse(deleted=True, hashed_session_id=hashed)


@router.delete("/v1/status/{session_id}", response_model=DeleteResponse, include_in_schema=False)
async def delete_status_legacy(
    session_id: str, request: Request, db: Database, payload: AuthPayload
) -> DeleteResponse:
    return await delete_callstate(session_id, request, db, payload)


@router.post("/v1/revoke")
async def revoke(request: Request, db: Database, payload: AuthPayload) -> dict[str, Any]:
    await apply_authenticated_limit(request, payload)
    now = datetime.now(UTC)
    token_expiry = datetime.fromtimestamp(payload["exp"], tz=UTC)
    expires = max(
        token_expiry,
        now + timedelta(seconds=request.app.state.settings.revocation_retention_seconds),
    )
    existing = await db.get(RevokedToken, payload["jti"])
    if not existing:
        db.add(
            RevokedToken(
                jti=payload["jti"],
                owner_hash=payload["owner_hash"],
                revoked_at=now,
                expires_at=expires,
            )
        )
        await db.commit()
    logger.info("token_revoked", owner_ref=payload["owner_hash"][:12])
    return {"revoked": True, "jti": payload["jti"]}


@router.get("/v1/notifications")
async def list_notifications(
    request: Request,
    db: Database,
    payload: AuthPayload,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[dict[str, Any]]:
    await apply_authenticated_limit(request, payload)
    result = await db.execute(
        select(NotificationRecord)
        .where(NotificationRecord.owner_hash == payload["owner_hash"])
        .order_by(NotificationRecord.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": row.id,
            "hashed_session_id": row.hashed_id[:8] + "...",
            "event": row.event,
            "message": row.message,
            "severity": row.severity,
            "created_at": row.created_at.isoformat(),
        }
        for row in result.scalars().all()
    ]
