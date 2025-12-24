"""Search routes - 100% Django + Django Ninja + Django ORM.

All database access through Django ORM models.
All strings use centralized messages for i18n.
"""

from typing import Any

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from common.utils.logger import get_logger

from ..messages import ErrorCode, get_message
from ..schemas import MemorySearchRequest, MemorySearchResponse

logger = get_logger(__name__)
router = Router(tags=["memories"])


def _get_service():
    """Get the memory service instance."""
    from somafractalmemory.api.core import get_mem

    return get_mem()


def _get_tenant_from_request(request: HttpRequest) -> str:
    """Extract tenant from request headers."""
    tenant = request.headers.get("X-Soma-Tenant")
    if tenant:
        return tenant.strip()
    return "default"


def _check_auth(request: HttpRequest) -> None:
    """Check API token authentication."""
    from somafractalmemory.api.core import API_TOKEN

    if not API_TOKEN:
        return

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HttpError(401, get_message(ErrorCode.MISSING_AUTH_HEADER))

    provided = auth_header.split(" ", 1)[1]
    if provided != API_TOKEN:
        raise HttpError(401, get_message(ErrorCode.INVALID_API_TOKEN))


@router.get("/search", response=MemorySearchResponse)
def search_memories_get(
    request: HttpRequest,
    query: str,
    top_k: int = 5,
    filters: str | None = None,
) -> MemorySearchResponse:
    """GET version of the memory search endpoint using Django ORM."""
    _check_auth(request)

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
        except Exception:
            pass

    results = service.search(
        query=query,
        top_k=top_k,
        tenant=tenant,
        filters=parsed_filters,
    )

    return MemorySearchResponse(memories=results)


@router.post("/search", response=MemorySearchResponse)
def search_memories(request: HttpRequest, req: MemorySearchRequest) -> MemorySearchResponse:
    """POST version of the memory search endpoint using Django ORM."""
    _check_auth(request)

    service = _get_service()
    tenant = _get_tenant_from_request(request)

    results = service.search(
        query=req.query,
        top_k=req.top_k,
        tenant=tenant,
        filters=req.filters,
    )

    return MemorySearchResponse(memories=results)
