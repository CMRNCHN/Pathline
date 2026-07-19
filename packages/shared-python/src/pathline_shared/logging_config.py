from __future__ import annotations

import structlog

from .crypto import redact_dict


SENSITIVE_LOG_KEYS = {
    "access_token",
    "authorization",
    "encrypted_payload",
    "jwt",
    "nonce",
    "password",
    "phone",
    "session_id",
    "target_number",
    "token",
}


def redact_event(
    _logger: object,
    _method_name: str,
    event_dict: dict[str, object],
) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for key, value in event_dict.items():
        if key.lower() in SENSITIVE_LOG_KEYS:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = redact_dict(value)
        else:
            sanitized[key] = value
    return redact_dict(sanitized)


def configure_logging(service_name: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            redact_event,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str):
    return structlog.get_logger(name)
