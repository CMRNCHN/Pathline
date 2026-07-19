from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from pathline_shared.crypto import hash_session_id

from .database import get_db
from .models import RevokedToken

security = HTTPBearer(auto_error=False)


def owner_hash(token_id: str, pepper: str) -> str:
    """Derive a capability owner without trusting the caller-supplied user label."""
    return hash_session_id(f"owner-token:{token_id}", pepper)


def artifact_hash(session_id: str, owner: str, pepper: str) -> str:
    return hash_session_id(f"artifact:{owner}:{session_id}", pepper)


def mint_token(user_id: str, consent_version: str, request: Request) -> tuple[str, int, str]:
    settings = request.app.state.settings
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


async def verify_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing authorization")
    settings = request.app.state.settings
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "jti", "iat", "exp", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    if payload.get("type") != "ephemeral":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
    if not isinstance(payload.get("sub"), str) or not payload["sub"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token owner")

    revoked = await db.get(RevokedToken, payload["jti"])
    if revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revoked")
    payload["owner_hash"] = owner_hash(payload["jti"], settings.session_pepper)
    return payload
