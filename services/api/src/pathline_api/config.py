from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


DEVELOPMENT_JWT_SECRET = "dev-secret-change-me"
DEVELOPMENT_SESSION_PEPPER = "dev-pepper-change-me"


class Settings(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite+aiosqlite:///./pathline.db"
    jwt_secret: str = DEVELOPMENT_JWT_SECRET
    jwt_ttl_seconds: int = 300
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    session_pepper: str = DEVELOPMENT_SESSION_PEPPER
    retention_seconds: int = 3600
    notification_retention_seconds: int = 3600
    revocation_retention_seconds: int = 86400
    purge_interval_seconds: int = 300
    purge_stale_after_seconds: int = 900
    cors_origins: Annotated[list[str], NoDecode] = []
    max_request_bytes: int = 1_100_000
    max_session_id_length: int = 128
    max_encrypted_payload_bytes: int = 1_048_576
    max_nonce_length: int = 256
    rate_limit_window_seconds: int = 60
    token_rate_limit: int = 20
    authenticated_rate_limit: int = 120
    auto_create_schema: bool = True

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_security_profile(self) -> "Settings":
        positive_fields = (
            "jwt_ttl_seconds",
            "retention_seconds",
            "notification_retention_seconds",
            "revocation_retention_seconds",
            "purge_interval_seconds",
            "purge_stale_after_seconds",
            "max_request_bytes",
            "max_session_id_length",
            "max_encrypted_payload_bytes",
            "max_nonce_length",
            "rate_limit_window_seconds",
            "token_rate_limit",
            "authenticated_rate_limit",
        )
        for name in positive_fields:
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")

        if self.app_env != "production":
            return self

        if not self.database_url.startswith(("postgresql+asyncpg://", "postgres+asyncpg://")):
            raise ValueError("production requires PostgreSQL via asyncpg")
        if self.jwt_secret == DEVELOPMENT_JWT_SECRET or len(self.jwt_secret) < 32:
            raise ValueError("production requires a managed JWT_SECRET of at least 32 characters")
        if self.session_pepper == DEVELOPMENT_SESSION_PEPPER or len(self.session_pepper) < 32:
            raise ValueError("production requires a managed SESSION_PEPPER of at least 32 characters")
        if self.auto_create_schema:
            raise ValueError("production requires AUTO_CREATE_SCHEMA=false and managed migrations")
        if not self.cors_origins:
            raise ValueError("production requires an explicit CORS_ORIGINS allowlist")
        if "*" in self.cors_origins:
            raise ValueError("wildcard CORS is not allowed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
