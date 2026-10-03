"""Standardized logging for SomaFractalMemory.

structlog is the logging backend. It is a required dependency
(``pyproject.toml``). There is no silent fallback to stdlib logging: a missing
backend is a deployment error and must refuse to import, not quietly change
the log format or drop structured fields.
"""

import logging
import os
import sys
from typing import Any

try:
    import structlog
    from structlog.stdlib import LoggerFactory
except ImportError as exc:  # pragma: no cover - depends on the deployment image
    raise ImportError(
        "structlog is required for SomaFractalMemory logging. Install with: pip install structlog"
    ) from exc


def get_logger(name: str) -> Any:
    """Standardized logger factory for SomaFractalMemory."""
    # Ensure name is properly scoped
    if not name.startswith("somafractalmemory"):
        if name == "__main__":
            name = "somafractalmemory.main"
        else:
            name = f"somafractalmemory.{name}"

    return structlog.get_logger(name)


def configure_logging(service_name: str, level: str = "INFO") -> Any:
    """Configure global logging for a service."""
    log_level = os.environ.get("SOMA_LOG_LEVEL", level).upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (
                structlog.processors.JSONRenderer()
                if os.environ.get("SOMA_LOG_JSON", "false").lower() == "true"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    return get_logger(service_name)
