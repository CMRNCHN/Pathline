from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from pathline_shared.logging_config import configure_logging, get_logger
from pathline_shared.models import DIDRecord

configure_logging("did-manager")
logger = get_logger("did-manager")

app = FastAPI(title="Pathline DID Manager", version="0.1.0")


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    cooldown_seconds: int = 3600
    did_pool_path: str = "data/did_pool.json"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
redis_client: redis.Redis | None = None


class DIDAssignment(BaseModel):
    number: str
    provider: str
    session_id: str


class DIDPoolConfig(BaseModel):
    dids: list[DIDRecord]


DEFAULT_POOL = DIDPoolConfig(
    dids=[
        DIDRecord(number="+15550001001", provider="provider_a", status="active"),
        DIDRecord(number="+15550001002", provider="provider_a", status="active"),
        DIDRecord(number="+15550002001", provider="provider_b", status="active"),
        DIDRecord(number="+15550002002", provider="provider_b", status="active"),
    ]
)


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


def load_pool() -> DIDPoolConfig:
    path = Path(settings.did_pool_path)
    if path.exists():
        return DIDPoolConfig.model_validate_json(path.read_text())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_POOL.model_dump_json(indent=2))
    return DEFAULT_POOL


async def verify_auth(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization required")
    return authorization


@app.on_event("startup")
async def startup():
    await get_redis()
    load_pool()
    logger.info("did_manager_started")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "did-manager"}


@app.get("/v1/pool", response_model=DIDPoolConfig)
async def list_pool(_: str = Depends(verify_auth)):
    pool = load_pool()
    r = await get_redis()
    now = datetime.now(UTC)

    enriched = []
    for did in pool.dids:
        cooldown_key = f"did:cooldown:{did.number}"
        cooldown_until = await r.get(cooldown_key)
        last_used = await r.get(f"did:last_used:{did.number}")
        enriched.append(
            DIDRecord(
                number=did.number,
                provider=did.provider,
                status="cooldown" if cooldown_until else did.status,
                last_used_at=last_used,
                cooldown_until=cooldown_until,
            )
        )
    return DIDPoolConfig(dids=enriched)


@app.post("/v1/assign", response_model=DIDAssignment)
async def assign_did(session_id: str, _: str = Depends(verify_auth)):
    """Select an available DID with provider distribution and cooldown enforcement."""
    pool = load_pool()
    r = await get_redis()
    now = datetime.now(UTC)

    available: list[DIDRecord] = []
    for did in pool.dids:
        if did.status != "active":
            continue
        cooldown_key = f"did:cooldown:{did.number}"
        if await r.exists(cooldown_key):
            continue
        available.append(did)

    if not available:
        raise HTTPException(503, "No DIDs available — all in cooldown")

    # Round-robin across providers for distribution
    provider_counts: dict[str, int] = {}
    for did in available:
        provider_counts[did.provider] = provider_counts.get(did.provider, 0)

    selected = min(available, key=lambda d: (provider_counts.get(d.provider, 0), d.number))

    cooldown_until = now + timedelta(seconds=settings.cooldown_seconds)
    await r.setex(
        f"did:cooldown:{selected.number}",
        settings.cooldown_seconds,
        cooldown_until.isoformat(),
    )
    await r.set(f"did:last_used:{selected.number}", now.isoformat())
    await r.set(f"did:session:{session_id}", json.dumps({"number": selected.number, "provider": selected.provider}))

    logger.info(
        "did_assigned",
        session_id=session_id[:8] + "...",
        provider=selected.provider,
    )
    return DIDAssignment(number=selected.number, provider=selected.provider, session_id=session_id)


@app.post("/v1/release")
async def release_did(session_id: str, _: str = Depends(verify_auth)):
    r = await get_redis()
    await r.delete(f"did:session:{session_id}")
    logger.info("did_released", session_id=session_id[:8] + "...")
    return {"released": True}
