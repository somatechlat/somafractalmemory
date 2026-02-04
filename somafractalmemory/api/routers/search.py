"""Search routes - 100% Django + Django Ninja + Django ORM.

All database access through Django ORM models.
All strings use centralized messages for i18n.
"""

from typing import Any

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from somafractalmemory.apps.aaas.auth import MultiAuth, can_access_namespace, has_permission
from somafractalmemory.apps.common.messages import ErrorCode, get_message
from somafractalmemory.apps.common.utils.logger import get_logger

from ..schemas import MemorySearchRequest, MemorySearchResponse

logger = get_logger(__name__)
router = Router(tags=["memories"])


def _get_service():
    """Get the memory service instance."""
    from somafractalmemory.api.core import get_mem

    return get_mem()


def _get_tenant_from_request(request: HttpRequest) -> str:
    """Extract tenant from request headers."""
    auth = getattr(request, "auth", {}) or {}
    if auth.get("tenant"):
        return auth["tenant"]
    tenant = request.headers.get("X-Soma-Tenant")
    if tenant:
        return tenant.strip()
    return "default"


def _ensure_permission(request: HttpRequest, permission: str) -> None:
    """Ensure caller has the required permission."""
    if not has_permission(request, permission):
        raise HttpError(403, get_message(ErrorCode.PERMISSION_DENIED))


def _ensure_namespace_access(request: HttpRequest) -> None:
    """Ensure caller can access the current namespace."""
    from somafractalmemory.api.core import get_mem

    namespace = get_mem().namespace
    if not can_access_namespace(request, namespace):
        raise HttpError(403, get_message(ErrorCode.PERMISSION_DENIED))


@router.get("/search", response=MemorySearchResponse, auth=MultiAuth())
def search_memories_get(
    request: HttpRequest,
    query: str,
    top_k: int = 5,
    filters: str | None = None,
) -> MemorySearchResponse:
    """GET version of the memory search endpoint using Django ORM."""
    _ensure_permission(request, "read")
    _ensure_namespace_access(request)

    service = _get_service()
    tenant = _get_tenant_from_request(request)

    # Parse filters if provided
    parsed_filters: dict[str, Any] | None = None
    if filters:
        import json

        try:
            parsed_candidate = json.loads(filters)
            if isinstance(parsed_candidate, dict):
                parsed_filters = parsed_candidate
        except Exception as e:
            logger.warning(f"Failed to parse search filters JSON: {e}")

    results = service.search(
        query=query,
        top_k=top_k,
        tenant=tenant,
        filters=parsed_filters,
    )

    return MemorySearchResponse(memories=results)


@router.post("/search", response=MemorySearchResponse, auth=MultiAuth())
def search_memories(request: HttpRequest, req: MemorySearchRequest) -> MemorySearchResponse:
    """POST version of the memory search endpoint using Django ORM."""
    _ensure_permission(request, "read")
    _ensure_namespace_access(request)

    service = _get_service()
    tenant = _get_tenant_from_request(request)

    results = service.search(
        query=req.query,
        top_k=req.top_k,
        tenant=tenant,
        filters=req.filters,
    )

    return MemorySearchResponse(memories=results)
