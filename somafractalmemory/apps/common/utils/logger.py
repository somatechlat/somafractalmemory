import logging
import os
import sys
from typing import Any

# Try to import structlog for premium logging, fallback to standard logging
try:
    import structlog
    from structlog.stdlib import LoggerFactory

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


def get_logger(name: str) -> Any:
    """Standardized logger factory for SomaFractalMemory."""
    # Ensure name is properly scoped
    if not name.startswith("somafractalmemory"):
        if name == "__main__":
            name = "somafractalmemory.main"
        else:
            name = f"somafractalmemory.{name}"

    if HAS_STRUCTLOG:
        return structlog.get_logger(name)

    logger = logging.getLogger(name)
    log_level = os.environ.get("SOMA_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(level)
    return logger


def configure_logging(service_name: str, level: str = "INFO") -> Any:
    """Configure global logging for a service."""
    log_level = os.environ.get("SOMA_LOG_LEVEL", level).upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    if HAS_STRUCTLOG:
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
