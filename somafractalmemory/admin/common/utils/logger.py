"""Standardized logging for SomaFractalMemory.

structlog is the logging backend. It is a required dependency
(``pyproject.toml``). There is no silent fallback to stdlib logging: a missing
backend is a deployment error and must refuse to import, not quietly change
the log format or drop structured fields.

Level and JSON mode come from the settings model (``SOMA_LOG_LEVEL`` /
``SOMA_LOG_JSON``). They are not read from ``os.environ`` here: the deployment
authority is Django settings, which already applied the env override and the
schema default.
"""

import logging
import sys
from typing import Any

from django.core.exceptions import ImproperlyConfigured

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


def configure_logging(service_name: str, level: str | None = None) -> Any:
    """Configure global logging for a service.

    Args:
        service_name: Logger name returned to the caller.
        level: Optional explicit level. When omitted, ``SOMA_LOG_LEVEL`` from
            the settings model is used. Passing it is legal only for callers
            that configure logging outside Django; inside Django the settings
            model is the deployment authority.

    Raises:
        ImproperlyConfigured: the resolved level name is not a logging level
            (Rule 91 — a typo is not permission to invent INFO).
    """
    from somafractalmemory.settings.model import resolve_setting

    log_level_name = str(level or resolve_setting("SOMA_LOG_LEVEL")).upper()
    numeric_level = getattr(logging, log_level_name, None)
    if numeric_level is None:
        raise ImproperlyConfigured(
            f"log level {log_level_name!r} is not a Python logging level. "
            "VIBE Rule 91: an unparseable setting is not permission to invent a value."
        )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (
                structlog.processors.JSONRenderer()
                if bool(resolve_setting("SOMA_LOG_JSON"))
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
