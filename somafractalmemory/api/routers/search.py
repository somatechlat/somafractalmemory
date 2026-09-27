"""Search routes - 100% Django + Django Ninja + Django ORM.

All database access through Django ORM models.
All strings use centralized messages for i18n.
Auth via standalone facade — zero AAAS dependency.
"""

from typing import Any

from django.http import HttpRequest
from ninja import Router

from somafractalmemory.admin.common.utils.logger import get_logger
from somafractalmemory.api.auth import StandaloneAuth
from somafractalmemory.api.utils import (
    ensure_embedding_dim,
    ensure_namespace_access,
    ensure_permission,
    get_tenant_from_request,
)

from ..schemas import MemorySearchRequest, MemorySearchResponse

logger = get_logger(__name__)
router = Router(tags=["memories"])


def _get_service():
    """Get the memory service instance."""
    from somafractalmemory.api.core import get_mem

    return get_mem()


@router.get("/search", response=MemorySearchResponse, auth=StandaloneAuth())
def search_memories_get(
    request: HttpRequest,
    query: str,
    top_k: int = 5,
    offset: int = 0,
    filters: str | None = None,
    tenant_id: str | None = None,
) -> MemorySearchResponse:
    """GET version of the memory search endpoint using Django ORM.

    Supports pagination with offset parameter.
    """
    ensure_permission(request, "read")
    service = _get_service()
    ensure_namespace_access(request, service.namespace)

    tenant = get_tenant_from_request(request, explicit_tenant=tenant_id)

    # Parse filters if provided
    parsed_filters: dict[str, Any] | None = None
    if filters:
        import json

        try:
            parsed_candidate = json.loads(filters)
            if isinstance(parsed_candidate, dict):
                parsed_filters = parsed_candidate
        except Exception as e:
            logger.warning("Failed to parse search filters JSON: %s", e)

    results = service.search(
        query=query,
        top_k=top_k,
        offset=offset,
        tenant=tenant,
        filters=parsed_filters,
    )

    return MemorySearchResponse(memories=results)


@router.post("/search", response=MemorySearchResponse, auth=StandaloneAuth())
def search_memories(request: HttpRequest, req: MemorySearchRequest) -> MemorySearchResponse:
    """POST version of the memory search endpoint using Django ORM.

    Accepts an optional precomputed query ``embedding`` (ranked by vector
    similarity) and an optional ``tenant_id`` scoping the search.
    """
    ensure_permission(request, "read")
    service = _get_service()
    ensure_namespace_access(request, service.namespace)

    ensure_embedding_dim(req.embedding)
    tenant = get_tenant_from_request(request, explicit_tenant=req.tenant_id)

    results = service.search(
        query=req.query,
        top_k=req.top_k,
        offset=req.offset,
        memory_type=req.memory_type,
        tenant=tenant,
        filters=req.filters,
        query_embedding=req.embedding,
    )

    return MemorySearchResponse(memories=results)
