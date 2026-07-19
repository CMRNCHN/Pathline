from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select

from pathline_shared.logging_config import configure_logging, get_logger

from .config import Settings, get_settings
from .database import create_database, database_is_ready, initialize_database
from .middleware import CorrelationIdMiddleware, RateLimiter, RequestSizeLimitMiddleware
from .models import CallStateRecord, ConsentAudit, IdempotencyRecord, NotificationRecord, RevokedToken
from .routes import router

configure_logging("api")
logger = get_logger("api")


async def purge_once(app: FastAPI) -> None:
    now = datetime.now(UTC)
    async with app.state.session_factory() as db:
        expired_artifacts = select(CallStateRecord.hashed_id).where(CallStateRecord.expires_at <= now)
        await db.execute(
            delete(NotificationRecord).where(
                (NotificationRecord.expires_at <= now)
                | (NotificationRecord.hashed_id.in_(expired_artifacts))
            )
        )
        await db.execute(delete(CallStateRecord).where(CallStateRecord.expires_at <= now))
        await db.execute(delete(ConsentAudit).where(ConsentAudit.expires_at <= now))
        await db.execute(delete(RevokedToken).where(RevokedToken.expires_at <= now))
        await db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.expires_at <= now))
        await db.commit()
    app.state.last_purge_success = now
    logger.info("purge_completed")


async def purge_expired(app: FastAPI) -> None:
    while True:
        try:
            await purge_once(app)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("purge_failed")
        await asyncio.sleep(app.state.settings.purge_interval_seconds)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    engine, session_factory = create_database(app_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        await initialize_database(engine, app_settings)
        application.state.last_purge_success = None
        purge_task = asyncio.create_task(purge_expired(application), name="pathline-retention-purge")
        logger.info("api_started", mode="v1-thin", environment=app_settings.app_env)
        try:
            yield
        finally:
            purge_task.cancel()
            with suppress(asyncio.CancelledError):
                await purge_task
            await engine.dispose()
            logger.info("api_stopped")

    application = FastAPI(title="Pathline API (v1)", version="0.2.0", lifespan=lifespan)
    application.state.settings = app_settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.rate_limiter = RateLimiter(app_settings.rate_limit_window_seconds)
    application.state.last_purge_success = None

    application.add_middleware(RequestSizeLimitMiddleware, max_bytes=app_settings.max_request_bytes)
    application.add_middleware(CorrelationIdMiddleware)
    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "api", "version": "v1", "mode": "client_mediated_only"}

    @application.get("/ready")
    async def ready(request: Request) -> dict[str, str]:
        database_ready = await database_is_ready(request.app.state.engine)
        last_purge = request.app.state.last_purge_success
        purge_ready = bool(
            last_purge
            and datetime.now(UTC) - last_purge
            <= timedelta(seconds=request.app.state.settings.purge_stale_after_seconds)
        )
        if not database_ready or not purge_ready:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "database": "ok" if database_ready else "unavailable",
                    "purge_worker": "ok" if purge_ready else "stale",
                },
            )
        return {"status": "ready", "database": "ok", "purge_worker": "ok"}

    application.include_router(router)
    return application


app = create_app()
