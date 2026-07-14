from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic_settings import BaseSettings

from pathline_shared.logging_config import configure_logging, get_logger
from pathline_shared.models import TokenRequest, TokenResponse

configure_logging("auth")
logger = get_logger("auth")

app = FastAPI(title="Pathline Auth Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)


class Settings(BaseSettings):
    jwt_secret: str = "dev-secret-change-me"
    jwt_ttl_seconds: int = 300
    jwt_algorithm: str = "HS256"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()


def create_ephemeral_token(user_id: str, call_mode: str, consent_version: str) -> tuple[str, int]:
    """Mint a short-lived per-session token."""
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.jwt_ttl_seconds)
    payload = {
        "sub": user_id,
        "jti": jti,
        "call_mode": call_mode,
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
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth"}


@app.post("/v1/token", response_model=TokenResponse)
async def mint_token(request: TokenRequest):
    if not request.consent.accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Consent required")

    token, ttl = create_ephemeral_token(
        request.user_id,
        request.call_mode.value,
        request.consent.terms_version,
    )
    logger.info(
        "token_minted",
        user_id=request.user_id,
        call_mode=request.call_mode.value,
        consent_version=request.consent.terms_version,
    )
    return TokenResponse(access_token=token, expires_in=ttl)


@app.get("/v1/verify")
async def verify(payload: dict = Depends(verify_token)):
    return {"valid": True, "sub": payload.get("sub"), "call_mode": payload.get("call_mode")}


@app.post("/v1/revoke")
async def revoke(payload: dict = Depends(verify_token)):
    """Revoke session — tokens are short-lived; log revocation for audit."""
    logger.info("token_revoked", jti=payload.get("jti"), sub=payload.get("sub"))
    return {"revoked": True, "jti": payload.get("jti")}
