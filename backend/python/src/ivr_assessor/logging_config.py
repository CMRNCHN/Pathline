"""Structured logging configuration using structlog.

Call configure_logging() once at startup (e.g., in cli.py or the ASGI app
lifespan). After that, use structlog.get_logger() anywhere — or continue
using stdlib logging, which is captured via the structlog stdlib integration.

Context binding:
    structlog.contextvars.bind_contextvars(call_sid="CA123", session_id="abc")
    # All subsequent log calls in this async context include call_sid/session_id.
    structlog.contextvars.clear_contextvars()

JSON output (for Docker / log aggregators):
    LOG_FORMAT=json  in .env or environment
"""
from __future__ import annotations

import logging
import os
import sys


def _configure_stdlib_logging(log_level: int) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
            "%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def configure_logging(
    level: str | None = None,
    json_output: bool | None = None,
) -> None:
    """Configure structlog + stdlib logging.

    level:       log level string (default: LOG_LEVEL env var or "INFO")
    json_output: emit JSON lines (default: LOG_FORMAT=json env var)
    """
    log_level_str = level or os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    use_json = json_output if json_output is not None else (
        os.getenv("LOG_FORMAT", "").lower() == "json"
    )

    try:
        import structlog
    except ModuleNotFoundError:
        _configure_stdlib_logging(log_level)
        return

    # Shared processors for both structlog-native and stdlib-captured records.
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if use_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Quiet noisy libraries.
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
