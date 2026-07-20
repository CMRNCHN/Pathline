from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from pathline_shared.logging_config import get_logger

from .config import Settings
from .models import Base

logger = get_logger("api.database")

# Columns introduced by the owner-bound storage hardening. create_all does not
# ALTER existing tables, so older local SQLite files need an explicit rebuild.
REQUIRED_COLUMNS: dict[str, set[str]] = {
    "callstate_records": {"owner_hash", "payload_digest", "updated_at"},
    "notifications": {"owner_hash", "expires_at"},
    "consent_audits": {"owner_hash"},
    "revoked_tokens": {"owner_hash"},
    "idempotency_records": {"owner_hash", "idempotency_key"},
}


def create_database(settings: Settings) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


def _schema_matches_models(sync_connection) -> bool:
    inspector = inspect(sync_connection)
    for table_name, required in REQUIRED_COLUMNS.items():
        if not inspector.has_table(table_name):
            return False
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        if not required.issubset(existing):
            return False
    return True


async def initialize_database(engine: AsyncEngine, settings: Settings) -> None:
    if not settings.auto_create_schema:
        return

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        matches = await connection.run_sync(_schema_matches_models)
        if matches:
            return

        if settings.app_env == "production":
            raise RuntimeError(
                "Database schema is out of date. Set AUTO_CREATE_SCHEMA=false and run "
                "`alembic upgrade head` before starting the API."
            )

        logger.warning(
            "schema_drift_recreating",
            environment=settings.app_env,
            database=settings.database_url.split("://", 1)[-1],
        )
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


async def database_is_ready(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session
