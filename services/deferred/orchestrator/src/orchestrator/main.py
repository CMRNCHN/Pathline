from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
from sqlalchemy import Column, DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from promptpath_shared.crypto import hash_session_id
from promptpath_shared.logging_config import configure_logging, get_logger
from promptpath_shared.models import (
    CallMode,
    CallRequest,
    CallSession,
    CallStatus,
    StatusReport,
)

configure_logging("orchestrator")
logger = get_logger("orchestrator")

app = FastAPI(title="PromptPath Call Orchestrator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://promptpath:promptpath@localhost:5432/promptpath"
    did_manager_url: str = "http://localhost:8002"
    stt_service_url: str = "http://localhost:8004"
    notifications_url: str = "http://localhost:8005"
    kms_url: str = "http://localhost:8006"
    session_pepper: str = "dev-pepper-change-me"
    sip_tls_required: bool = True
    dtls_srtp_required: bool = True

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"

    hashed_id = Column(String(64), primary_key=True)
    status = Column(String(32), nullable=False)
    call_mode = Column(String(32), nullable=False)
    did_assigned = Column(String(32), nullable=True)
    provider = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def verify_auth(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization required")
    return authorization


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("orchestrator_started")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "orchestrator",
        "sip_tls_required": settings.sip_tls_required,
        "dtls_srtp_required": settings.dtls_srtp_required,
    }


@app.post("/v1/calls", response_model=CallSession)
async def initiate_call(
    request: CallRequest,
    auth: str = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
):
    session_id = str(uuid.uuid4())
    hashed = hash_session_id(session_id, settings.session_pepper)
    now = datetime.now(UTC)

    record = SessionRecord(
        hashed_id=hashed,
        status=CallStatus.PENDING.value,
        call_mode=request.call_mode.value,
        created_at=now,
        updated_at=now,
    )

    if request.call_mode == CallMode.SERVER_MEDIATED:
        async with httpx.AsyncClient() as client:
            did_resp = await client.post(
                f"{settings.did_manager_url}/v1/assign",
                params={"session_id": session_id},
                headers={"Authorization": auth},
                timeout=10.0,
            )
            if did_resp.status_code != 200:
                raise HTTPException(503, "DID assignment failed")
            did_data = did_resp.json()
            record.did_assigned = did_data["number"]
            record.provider = did_data["provider"]
            record.status = CallStatus.IN_PROGRESS.value

            # PJSIP agent would place call here with TLS + DTLS-SRTP
            logger.info(
                "server_call_initiated",
                hashed_id=hashed[:8] + "...",
                provider=did_data["provider"],
                tls=settings.sip_tls_required,
                dtls_srtp=settings.dtls_srtp_required,
            )
    else:
        logger.info("client_mediated_call_registered", hashed_id=hashed[:8] + "...")

    db.add(record)
    await db.commit()

    return CallSession(
        session_id=session_id,
        status=CallStatus(record.status),
        call_mode=request.call_mode,
        hashed_session_id=hashed,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        did_assigned=record.did_assigned,
        provider=record.provider,
    )


@app.post("/v1/calls/{session_id}/status", response_model=CallSession)
async def report_status(
    session_id: str,
    report: StatusReport,
    db: AsyncSession = Depends(get_db),
    auth: str = Depends(verify_auth),
):
    hashed = hash_session_id(session_id, settings.session_pepper)
    result = await db.execute(select(SessionRecord).where(SessionRecord.hashed_id == hashed))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Session not found")

    now = datetime.now(UTC)
    record.status = report.status.value
    record.updated_at = now
    await db.commit()

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{settings.notifications_url}/v1/notify",
            json={
                "session_id": session_id[:8] + "...",
                "event": "status_update",
                "message": f"Call status: {report.status.value}",
                "severity": "info" if report.status == CallStatus.COMPLETED else "warning",
            },
            timeout=5.0,
        )

    logger.info("status_reported", hashed_id=hashed[:8] + "...", status=report.status.value)
    return CallSession(
        session_id=session_id,
        status=report.status,
        call_mode=CallMode(record.call_mode),
        hashed_session_id=hashed,
        created_at=record.created_at.isoformat(),
        updated_at=now.isoformat(),
        did_assigned=record.did_assigned,
        provider=record.provider,
    )


@app.get("/v1/calls/{session_id}", response_model=CallSession)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db), auth: str = Depends(verify_auth)):
    hashed = hash_session_id(session_id, settings.session_pepper)
    result = await db.execute(select(SessionRecord).where(SessionRecord.hashed_id == hashed))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Session not found")
    return CallSession(
        session_id=session_id,
        status=CallStatus(record.status),
        call_mode=CallMode(record.call_mode),
        hashed_session_id=hashed,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
        did_assigned=record.did_assigned,
        provider=record.provider,
    )
