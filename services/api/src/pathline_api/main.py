from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Column, DateTime, String, Text, delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from pathline_shared.crypto import hash_session_id
from pathline_shared.logging_config import configure_logging, get_logger
from pathline_shared.models import ConsentRecord as ConsentPayload
from pathline_shared.models import TokenRequest, TokenResponse

configure_logging("api")
logger = get_logger("api")
security = HTTPBearer(auto_error=False)


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./pathline.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_ttl_seconds: int = 300
    jwt_algorithm: str = "HS256"
    session_pepper: str = "dev-pepper-change-me"
    retention_seconds: int = 3600
    purge_interval_seconds: int = 300

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
_revoked_jtis: set[str] = set()


class Base(DeclarativeBase):
    pass


class CallStateRecord(Base):
    __tablename__ = "callstate_records"

    hashed_id = Column(String(64), primary_key=True)
    encrypted_payload = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class NotificationRecord(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    hashed_id = Column(String(64), nullable=False)
    event = Column(String(64), nullable=False)
    message = Column(String(512), nullable=False)
    severity = Column(String(16), nullable=False, default="info")
    created_at = Column(DateTime(timezone=True), nullable=False)


class ConsentAudit(Base):
    """Immutable consent acceptance tied to ephemeral token (jti) and optional run session."""

    __tablename__ = "consent_audits"

    jti = Column(String(36), primary_key=True)
    hashed_user_id = Column(String(64), nullable=False, index=True)
    terms_version = Column(String(32), nullable=False)
    consent_at = Column(DateTime(timezone=True), nullable=False)
    call_mode = Column(String(32), nullable=False)
    hashed_session_id = Column(String(64), nullable=True, index=True)
    session_linked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class EncryptedCallStateIngest(BaseModel):
    """Opaque client-encrypted callstate — server cannot read contents."""
    session_id: str
    encrypted_payload: str
    payload_nonce: str


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
    session_id: str = Field(min_length=1)


class SessionLinkResponse(BaseModel):
    linked: bool
    hashed_session_id: str
    session_linked_at: str


def parse_consent_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


async def link_consent_to_session(
    db: AsyncSession,
    jti: str,
    session_id: str,
    *,
    now: datetime | None = None,
) -> ConsentAudit | None:
    record = await db.get(ConsentAudit, jti)
    if not record:
        return None
    linked_at = now or datetime.now(UTC)
    record.hashed_session_id = hash_session_id(session_id, settings.session_pepper)
    record.session_linked_at = linked_at
    return record


async def purge_expired():
    while True:
        try:
            now = datetime.now(UTC)
            async with SessionLocal() as db:
                await db.execute(delete(CallStateRecord).where(CallStateRecord.expires_at < now))
                await db.execute(delete(ConsentAudit).where(ConsentAudit.expires_at < now))
                await db.commit()
            logger.info("purge_completed")
        except Exception as exc:
            logger.error("purge_failed", error=str(exc))
        await asyncio.sleep(settings.purge_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    purge_task = asyncio.create_task(purge_expired())
    logger.info("api_started", mode="v1-thin")
    yield
    purge_task.cancel()


app = FastAPI(title="Pathline API (v1)", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db():
    async with SessionLocal() as session:
        yield session


def mint_token(user_id: str, consent_version: str) -> tuple[str, int, str]:
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.jwt_ttl_seconds)
    payload = {
        "sub": user_id,
        "jti": jti,
        "call_mode": "client_mediated",
        "consent_version": consent_version,
        "iat": now,
        "exp": expires,
        "type": "ephemeral",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_ttl_seconds, jti


def verify_token(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing authorization")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "ephemeral":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
        if payload.get("jti") in _revoked_jtis:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revoked")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api", "version": "v1", "mode": "client_mediated_only"}


@app.post("/v1/token", response_model=TokenResponse)
async def create_token(request: TokenRequest, db: AsyncSession = Depends(get_db)):
    if not request.consent.accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Consent required")
    if request.call_mode.value != "client_mediated":
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Server-mediated calls are v3. Use client-mediated flow.",
        )

    token, ttl, jti = mint_token(request.user_id, request.consent.terms_version)
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=ttl)
    consent_at = parse_consent_timestamp(request.consent.timestamp)

    db.add(
        ConsentAudit(
            jti=jti,
            hashed_user_id=hash_session_id(request.user_id, settings.session_pepper),
            terms_version=request.consent.terms_version,
            consent_at=consent_at,
            call_mode=request.call_mode.value,
            created_at=now,
            expires_at=expires,
        )
    )
    await db.commit()

    logger.info("consent_recorded", jti=jti, user_id=request.user_id[:8] + "...")
    return TokenResponse(access_token=token, expires_in=ttl)


@app.post("/v1/consent/session", response_model=SessionLinkResponse)
async def link_session_to_consent(
    body: SessionLinkRequest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    """Associate the current run session with the consent record for this token."""
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token missing jti")

    now = datetime.now(UTC)
    record = await link_consent_to_session(db, jti, body.session_id, now=now)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consent record not found")

    await db.commit()
    logger.info("consent_session_linked", jti=jti, hashed_session_id=record.hashed_session_id[:8] + "...")
    return SessionLinkResponse(
        linked=True,
        hashed_session_id=record.hashed_session_id or "",
        session_linked_at=now.isoformat(),
    )


@app.post("/v1/callstate", response_model=CallStateIngestResponse)
async def ingest_callstate(
    body: EncryptedCallStateIngest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    """Accept opaque encrypted callstate — no phone numbers, no plaintext."""
    hashed = hash_session_id(body.session_id, settings.session_pepper)
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.retention_seconds)

    import json
    stored = json.dumps({
        "encrypted_payload": body.encrypted_payload,
        "payload_nonce": body.payload_nonce,
    })

    existing = await db.get(CallStateRecord, hashed)
    if existing:
        existing.encrypted_payload = stored
        existing.expires_at = expires
    else:
        db.add(CallStateRecord(hashed_id=hashed, encrypted_payload=stored, created_at=now, expires_at=expires))

    jti = payload.get("jti")
    if jti:
        await link_consent_to_session(db, jti, body.session_id, now=now)

    notif = NotificationRecord(
        id=str(uuid.uuid4()),
        hashed_id=hashed,
        event="callstate_received",
        message="Encrypted callstate ingested",
        severity="info",
        created_at=now,
    )
    db.add(notif)
    await db.commit()

    logger.info("callstate_ingested", hashed_id=hashed[:8] + "...")
    return CallStateIngestResponse(
        hashed_session_id=hashed,
        received_at=now.isoformat(),
        expires_at=expires.isoformat(),
    )


@app.post("/v1/status", response_model=CallStateIngestResponse, include_in_schema=False)
async def ingest_status_legacy(
    body: EncryptedCallStateIngest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    return await ingest_callstate(body, db, payload)


@app.get("/v1/callstate/{session_id}/export", response_model=ExportResponse)
async def export_callstate(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    hashed = hash_session_id(session_id, settings.session_pepper)
    record = await db.get(CallStateRecord, hashed)
    if not record:
        raise HTTPException(404, "No data for session")

    import json
    data = json.loads(record.encrypted_payload)
    return ExportResponse(
        hashed_session_id=hashed,
        encrypted_payload=data["encrypted_payload"],
        payload_nonce=data["payload_nonce"],
        created_at=record.created_at.isoformat(),
        expires_at=record.expires_at.isoformat(),
    )


@app.get("/v1/status/{session_id}/export", response_model=ExportResponse, include_in_schema=False)
async def export_status_legacy(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    return await export_callstate(session_id, db, _)


@app.delete("/v1/callstate/{session_id}", response_model=DeleteResponse)
async def delete_callstate(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    hashed = hash_session_id(session_id, settings.session_pepper)
    record = await db.get(CallStateRecord, hashed)
    if record:
        await db.delete(record)
        await db.commit()
    logger.info("callstate_deleted", hashed_id=hashed[:8] + "...")
    return DeleteResponse(deleted=True, hashed_session_id=hashed)


@app.delete("/v1/status/{session_id}", response_model=DeleteResponse, include_in_schema=False)
async def delete_status_legacy(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    return await delete_callstate(session_id, db, _)


@app.post("/v1/revoke")
async def revoke(payload: dict = Depends(verify_token)):
    jti = payload.get("jti")
    if jti:
        _revoked_jtis.add(jti)
    logger.info("token_revoked", jti=jti)
    return {"revoked": True, "jti": jti}


@app.get("/v1/notifications")
async def list_notifications(limit: int = 20, _: dict = Depends(verify_token)):
    async with SessionLocal() as db:
        result = await db.execute(
            select(NotificationRecord).order_by(NotificationRecord.created_at.desc()).limit(limit)
        )
        rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "hashed_session_id": r.hashed_id[:8] + "...",
            "event": r.event,
            "message": r.message,
            "severity": r.severity,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
