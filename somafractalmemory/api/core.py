"""Core API module - 100% Django + Django Ninja + Django ORM.

This module initializes the Django Ninja API and uses Django ORM services.
All database access through Django ORM models.
NO external frameworks - pure Django.
"""

import os

# Django setup MUST happen before any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somafractalmemory.settings")

import django

django.setup()

from django.conf import settings
from django.http import HttpRequest
from ninja import NinjaAPI
from ninja.errors import HttpError

from common.utils.logger import configure_logging
from somafractalmemory.services import (
    get_graph_service,
    get_memory_service,
)

from .messages import ErrorCode, get_message

# Configure logging
logger = configure_logging(
    "somafractalmemory-api",
    level=getattr(settings, "SOMA_LOG_LEVEL", "INFO"),
).bind(component="django_api")


# -----------------------------------------------------------------------------
# API Token Loading
# -----------------------------------------------------------------------------
def _load_api_token() -> str | None:
    """Load the API token from Django settings."""
    token = getattr(settings, "SOMA_API_TOKEN", None)
    if token:
        return token

    # Use the helper function from settings if available
    if hasattr(settings, "get_api_token"):
        return settings.get_api_token()

    return None


API_TOKEN = _load_api_token()
if not API_TOKEN:
    raise RuntimeError("SOMA_API_TOKEN must be set before starting the SomaFractalMemory API.")


# -----------------------------------------------------------------------------
# Memory and Graph Services (Django ORM)
# -----------------------------------------------------------------------------
_namespace = getattr(settings, "SOMA_MEMORY_NAMESPACE", "api_ns")
mem_service = get_memory_service(namespace=_namespace)
graph_service = get_graph_service(namespace=_namespace)


# -----------------------------------------------------------------------------
# Django Ninja API Instance
# -----------------------------------------------------------------------------
api = NinjaAPI(
    title="SomaFractalMemory API",
    version="2.0.0",
    description="Cognitive memory system API (100% Django)",
)


# Exception handlers
@api.exception_handler(HttpError)
def handle_http_error(request: HttpRequest, exc: HttpError):
    """Handle HttpError exceptions."""
    return api.create_response(
        request,
        {"detail": str(exc)},
        status=exc.status_code,
    )


@api.exception_handler(Exception)
def handle_exception(request: HttpRequest, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"An unexpected error occurred: {exc}", exc_info=True)
    return api.create_response(
        request,
        {"detail": get_message(ErrorCode.INTERNAL_ERROR)},
        status=500,
    )


# -----------------------------------------------------------------------------
# API Accessors (for routers)
# -----------------------------------------------------------------------------
def get_mem():
    """Get the memory service instance."""
    return mem_service


def get_graph():
    """Get the graph service instance."""
    return graph_service


def get_rate_limiter():
    """Get rate limiter - placeholder for Django-based rate limiting."""
    return None  # Rate limiting can be implemented with Django middleware


# -----------------------------------------------------------------------------
# Register Routers
# -----------------------------------------------------------------------------
from .routers.graph import router as graph_router
from .routers.health import router as health_router
from .routers.memory import router as memory_router
from .routers.saas_admin import router as saas_admin_router
from .routers.search import router as search_router

api.add_router("/memories", memory_router, tags=["memories"])
api.add_router("/memories", search_router, tags=["memories"])
api.add_router("", health_router, tags=["system"])
api.add_router("/graph", graph_router, tags=["graph"])
api.add_router("/admin", saas_admin_router, tags=["SaaS Admin"])


__all__ = [
    "api",
    "get_mem",
    "get_graph",
    "get_rate_limiter",
    "API_TOKEN",
]
