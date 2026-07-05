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

from promptpath_shared.crypto import hash_session_id
from promptpath_shared.logging_config import configure_logging, get_logger
from promptpath_shared.models import ConsentRecord, TokenRequest, TokenResponse

configure_logging("api")
logger = get_logger("api")
security = HTTPBearer(auto_error=False)


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./promptpath.db"
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


class StatusRecord(Base):
    __tablename__ = "status_records"

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


class EncryptedStatusIngest(BaseModel):
    """Opaque client-encrypted status — server cannot read contents."""
    session_id: str
    encrypted_payload: str
    payload_nonce: str


class StatusIngestResponse(BaseModel):
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


async def purge_expired():
    while True:
        try:
            now = datetime.now(UTC)
            async with SessionLocal() as db:
                await db.execute(delete(StatusRecord).where(StatusRecord.expires_at < now))
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


app = FastAPI(title="PromptPath API (v1)", version="0.1.0", lifespan=lifespan)
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


def mint_token(user_id: str, consent_version: str) -> tuple[str, int]:
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
    return token, settings.jwt_ttl_seconds


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
async def create_token(request: TokenRequest):
    if not request.consent.accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Consent required")
    if request.call_mode.value != "client_mediated":
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Server-mediated calls are v3. Use client-mediated flow.",
        )

    token, ttl = mint_token(request.user_id, request.consent.terms_version)
    logger.info("token_minted", user_id=request.user_id[:8] + "...")
    return TokenResponse(access_token=token, expires_in=ttl)


@app.post("/v1/status", response_model=StatusIngestResponse)
async def ingest_status(
    body: EncryptedStatusIngest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    """Accept opaque encrypted status — no phone numbers, no plaintext."""
    hashed = hash_session_id(body.session_id, settings.session_pepper)
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.retention_seconds)

    import json
    stored = json.dumps({
        "encrypted_payload": body.encrypted_payload,
        "payload_nonce": body.payload_nonce,
    })

    existing = await db.get(StatusRecord, hashed)
    if existing:
        existing.encrypted_payload = stored
        existing.expires_at = expires
    else:
        db.add(StatusRecord(hashed_id=hashed, encrypted_payload=stored, created_at=now, expires_at=expires))

    notif = NotificationRecord(
        id=str(uuid.uuid4()),
        hashed_id=hashed,
        event="status_received",
        message="Encrypted status ingested",
        severity="info",
        created_at=now,
    )
    db.add(notif)
    await db.commit()

    logger.info("status_ingested", hashed_id=hashed[:8] + "...")
    return StatusIngestResponse(
        hashed_session_id=hashed,
        received_at=now.isoformat(),
        expires_at=expires.isoformat(),
    )


@app.get("/v1/status/{session_id}/export", response_model=ExportResponse)
async def export_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    hashed = hash_session_id(session_id, settings.session_pepper)
    record = await db.get(StatusRecord, hashed)
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


@app.delete("/v1/status/{session_id}", response_model=DeleteResponse)
async def delete_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_token),
):
    hashed = hash_session_id(session_id, settings.session_pepper)
    record = await db.get(StatusRecord, hashed)
    if record:
        await db.delete(record)
        await db.commit()
    logger.info("status_deleted", hashed_id=hashed[:8] + "...")
    return DeleteResponse(deleted=True, hashed_session_id=hashed)


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
