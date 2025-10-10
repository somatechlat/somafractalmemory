"""Shared structured logging configuration for Soma services."""

from __future__ import annotations

import logging

import structlog


def configure_logging(
    service_name: str, *, level: int | str = logging.INFO
) -> structlog.stdlib.BoundLogger:
    """Configure structlog for JSON output and return a service-bound logger."""

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(service=service_name)


def get_logger(service_name: str) -> structlog.stdlib.BoundLogger:
    """Return a logger without mutating global configuration."""

    return structlog.get_logger(service=service_name)


__all__ = ["configure_logging", "get_logger"]
