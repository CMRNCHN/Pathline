from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select, update

from pathline_api.config import Settings
from pathline_api.main import create_app, purge_once
from pathline_api.models import CallStateRecord, NotificationRecord

from .conftest import bearer, mint


async def ingest(
    client: AsyncClient,
    token: str,
    session_id: str,
    *,
    payload: str = "opaque-ciphertext",
    headers: dict[str, str] | None = None,
):
    request_headers = bearer(token)
    request_headers.update(headers or {})
    return await client.post(
        "/v1/callstate",
        headers=request_headers,
        json={
            "session_id": session_id,
            "encrypted_payload": payload,
            "payload_nonce": "opaque-nonce",
        },
    )


def test_production_profile_rejects_unsafe_defaults() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production")

    production = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://pathline@db/pathline",
        jwt_secret="j" * 32,
        session_pepper="p" * 32,
        cors_origins=["https://app.pathline.example"],
        auto_create_schema=False,
    )
    assert production.app_env == "production"


async def test_stale_sqlite_schema_is_rebuilt_in_development(tmp_path: Path) -> None:
    """Older local DBs used hashed_user_id; create_all alone cannot ALTER them."""
    import sqlite3

    from pathline_api.database import create_database, initialize_database

    db_path = tmp_path / "stale.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE consent_audits (
                jti VARCHAR(36) PRIMARY KEY,
                hashed_user_id VARCHAR(64) NOT NULL,
                terms_version VARCHAR(32) NOT NULL,
                consent_at DATETIME NOT NULL,
                call_mode VARCHAR(32) NOT NULL,
                hashed_session_id VARCHAR(64),
                session_linked_at DATETIME,
                created_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL
            )
            """
        )
        conn.commit()

    settings = Settings(
        app_env="development",
        database_url=f"sqlite+aiosqlite:///{db_path}",
        jwt_secret="test-jwt-secret-with-at-least-32-bytes",
        session_pepper="test-session-pepper-with-at-least-32-bytes",
        auto_create_schema=True,
    )
    engine, _ = create_database(settings)
    await initialize_database(engine, settings)
    await engine.dispose()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(consent_audits)")}
    assert "owner_hash" in columns
    assert "hashed_user_id" not in columns


async def test_owner_bound_export_delete_and_notifications(client: AsyncClient) -> None:
    alice = await mint(client, "alice")
    # Caller-supplied user labels are not accepted as proof of ownership.
    bob = await mint(client, "alice")
    assert (await ingest(client, alice, "shared-session")).status_code == 200

    assert (
        await client.get("/v1/callstate/shared-session/export", headers=bearer(bob))
    ).status_code == 404
    assert (
        await client.delete("/v1/callstate/shared-session", headers=bearer(bob))
    ).status_code == 200

    alice_notifications = await client.get("/v1/notifications", headers=bearer(alice))
    bob_notifications = await client.get("/v1/notifications", headers=bearer(bob))
    assert len(alice_notifications.json()) == 1
    assert bob_notifications.json() == []

    exported = await client.get("/v1/callstate/shared-session/export", headers=bearer(alice))
    assert exported.status_code == 200
    assert exported.json()["encrypted_payload"] == "opaque-ciphertext"

    deleted = await client.delete("/v1/callstate/shared-session", headers=bearer(alice))
    assert deleted.status_code == 200
    assert (await client.get("/v1/notifications", headers=bearer(alice))).json() == []


async def test_consent_token_cannot_cross_sessions(client: AsyncClient) -> None:
    token = await mint(client, "owner")
    linked = await client.post(
        "/v1/consent/session",
        headers=bearer(token),
        json={"session_id": "session-one"},
    )
    assert linked.status_code == 200
    assert (await ingest(client, token, "session-one")).status_code == 200
    assert (await ingest(client, token, "session-two")).status_code == 409


async def test_idempotent_ingest_and_conflict(client: AsyncClient) -> None:
    token = await mint(client, "owner")
    headers = {"Idempotency-Key": "run-final-state"}
    first = await ingest(client, token, "session-one", headers=headers)
    replay = await ingest(client, token, "session-one", headers=headers)
    conflict = await ingest(
        client,
        token,
        "session-one",
        payload="different-ciphertext",
        headers=headers,
    )
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    notifications = await client.get("/v1/notifications", headers=bearer(token))
    assert len(notifications.json()) == 1


async def test_revocation_survives_app_restart(settings: Settings) -> None:
    first_app = create_app(settings)
    async with first_app.router.lifespan_context(first_app):
        async with AsyncClient(
            transport=ASGITransport(app=first_app),
            base_url="http://testserver",
        ) as first_client:
            token = await mint(first_client, "owner")
            assert (await first_client.post("/v1/revoke", headers=bearer(token))).status_code == 200

    second_app = create_app(settings)
    async with second_app.router.lifespan_context(second_app):
        async with AsyncClient(
            transport=ASGITransport(app=second_app),
            base_url="http://testserver",
        ) as second_client:
            denied = await second_client.get("/v1/notifications", headers=bearer(token))
            assert denied.status_code == 401


async def test_retention_purges_artifact_and_notification(client: AsyncClient) -> None:
    token = await mint(client, "owner")
    assert (await ingest(client, token, "expired-session")).status_code == 200
    app = client._transport.app  # type: ignore[attr-defined]
    expired = datetime.now(UTC) - timedelta(seconds=1)
    async with app.state.session_factory() as db:
        await db.execute(update(CallStateRecord).values(expires_at=expired))
        await db.commit()

    await purge_once(app)
    async with app.state.session_factory() as db:
        artifact_count = await db.scalar(select(func.count()).select_from(CallStateRecord))
        notification_count = await db.scalar(select(func.count()).select_from(NotificationRecord))
    assert artifact_count == 0
    assert notification_count == 0


async def test_payload_bounds_correlation_and_readiness(client: AsyncClient) -> None:
    token = await mint(client, "owner")
    oversized = await ingest(client, token, "session", payload="x" * 1025)
    assert oversized.status_code in {413, 422}
    request_too_large = await client.post(
        "/v1/token",
        content=b"x" * 2049,
        headers={"Content-Type": "application/json"},
    )
    assert request_too_large.status_code == 413

    correlated = await client.get("/health", headers={"X-Request-ID": "safe-request-id"})
    assert correlated.headers["X-Request-ID"] == "safe-request-id"

    ready = await client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["purge_worker"] == "ok"


async def test_restricted_cors(database_url: str) -> None:
    settings = Settings(
        app_env="test",
        database_url=database_url,
        jwt_secret="test-jwt-secret-with-at-least-32-bytes",
        session_pepper="test-session-pepper-with-at-least-32-bytes",
        cors_origins=["https://allowed.example"],
        purge_interval_seconds=3600,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as cors_client:
            allowed = await cors_client.options(
                "/v1/token",
                headers={
                    "Origin": "https://allowed.example",
                    "Access-Control-Request-Method": "POST",
                },
            )
            denied = await cors_client.options(
                "/v1/token",
                headers={
                    "Origin": "https://denied.example",
                    "Access-Control-Request-Method": "POST",
                },
            )
    assert allowed.headers["access-control-allow-origin"] == "https://allowed.example"
    assert "access-control-allow-origin" not in denied.headers


async def test_token_rate_limit(database_url: str) -> None:
    settings = Settings(
        app_env="test",
        database_url=database_url,
        jwt_secret="test-jwt-secret-with-at-least-32-bytes",
        session_pepper="test-session-pepper-with-at-least-32-bytes",
        token_rate_limit=1,
        purge_interval_seconds=3600,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as limited_client:
            await mint(limited_client, "first")
            blocked = await limited_client.post(
                "/v1/token",
                json={
                    "user_id": "second",
                    "call_mode": "client_mediated",
                    "consent": {
                        "accepted": True,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "terms_version": "1.0",
                    },
                },
            )
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"
