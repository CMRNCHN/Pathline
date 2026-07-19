from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from pathline_api.config import Settings
from pathline_api.main import create_app


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'api-test.db'}"


@pytest.fixture
def settings(database_url: str) -> Settings:
    return Settings(
        app_env="test",
        database_url=database_url,
        jwt_secret="test-jwt-secret-with-at-least-32-bytes",
        session_pepper="test-session-pepper-with-at-least-32-bytes",
        purge_interval_seconds=3600,
        purge_stale_after_seconds=7200,
        rate_limit_window_seconds=60,
        token_rate_limit=100,
        authenticated_rate_limit=100,
        max_request_bytes=2048,
        max_encrypted_payload_bytes=1024,
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as test_client:
            yield test_client


async def mint(client: AsyncClient, user_id: str) -> str:
    response = await client.post(
        "/v1/token",
        json={
            "user_id": user_id,
            "call_mode": "client_mediated",
            "consent": {
                "accepted": True,
                "timestamp": datetime.now(UTC).isoformat(),
                "terms_version": "1.0",
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
