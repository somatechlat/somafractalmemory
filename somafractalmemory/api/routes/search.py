# somafractalmemory/api/routes/search.py
"""Search route handlers for SomaFractalMemory API.

Extracted from http_api.py for VIBE compliance (<500 lines per file).
"""

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request

from ..dependencies import auth_dep, get_tenant_from_request, rate_limit_dep
from ..schemas import MemorySearchRequest, MemorySearchResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/memories", tags=["memories"])


def get_mem():
    """Get the memory system instance. Imported at runtime to avoid circular imports."""
    from somafractalmemory.http_api import mem

    return mem


@router.get(
    "/search",
    response_model=MemorySearchResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.search"))],
)
def search_memories_get(
    query: str,
    top_k: int = 5,
    filters: str | None = None,
    request: Request = None,
) -> MemorySearchResponse:
    """GET version of the memory search endpoint.

    TENANT ISOLATION (D1): Results are filtered to only include memories
    belonging to the requesting tenant.
    """
    mem = get_mem()
    requesting_tenant = get_tenant_from_request(request) if request else "default"

    parsed_filters: dict[str, Any] | None = None
    if filters:
        try:
            parsed_candidate = json.loads(filters)
            if isinstance(parsed_candidate, dict):
                parsed_filters = parsed_candidate
        except Exception:
            parsed_filters = None

    if parsed_filters:
        results = mem.find_hybrid_by_type(query, top_k=top_k, filters=parsed_filters)
    else:
        results = mem.recall(query, top_k=top_k)

    # TENANT ISOLATION: Filter results to only include memories for this tenant
    filtered_results = []
    for result in results:
        stored_tenant = result.get("_tenant", "default")
        if stored_tenant == requesting_tenant:
            clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
            filtered_results.append(clean_result)

    return MemorySearchResponse(memories=filtered_results)


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.search"))],
)
def search_memories(req: MemorySearchRequest, request: Request = None) -> MemorySearchResponse:
    """POST version of the memory search endpoint."""
    mem = get_mem()

    if req.filters:
        results = mem.find_hybrid_by_type(req.query, top_k=req.top_k, filters=req.filters)
    else:
        results = mem.recall(req.query, top_k=req.top_k)

    return MemorySearchResponse(memories=results)
