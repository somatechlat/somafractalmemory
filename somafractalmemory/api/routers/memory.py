"""Memory CRUD routes - 100% Django + Django Ninja + Django ORM.

All database access through Django ORM models.
All strings use centralized messages for i18n.
Auth via standalone facade — zero AAAS dependency.
"""

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from somafractalmemory.admin.common.messages import ErrorCode, get_message
from somafractalmemory.admin.common.utils.logger import get_logger
from somafractalmemory.api.auth import StandaloneAuth
from somafractalmemory.api.utils import (
    ensure_embedding_dim,
    ensure_namespace_access,
    ensure_permission,
    get_tenant_from_request,
    safe_parse_coord,
)

from ..schemas import (
    MemoryDeleteResponse,
    MemoryGetResponse,
    MemoryStoreRequest,
    MemoryStoreResponse,
)

logger = get_logger(__name__)
router = Router(tags=["memories"])


def _get_service():
    """Get the memory service instance."""
    from somafractalmemory.api.core import get_mem

    return get_mem()


@router.post("", response=MemoryStoreResponse, auth=StandaloneAuth())
def store_memory(request: HttpRequest, req: MemoryStoreRequest) -> MemoryStoreResponse:
    """Store a memory using Django ORM.

    Accepts an optional precomputed ``embedding`` (stored verbatim) and an
    optional ``tenant_id`` scoping the write.
    """
    ensure_permission(request, "write")
    service = _get_service()
    ensure_namespace_access(request, service.namespace)

    coord = safe_parse_coord(req.coord)
    ensure_embedding_dim(req.embedding)
    tenant = get_tenant_from_request(request, explicit_tenant=req.tenant_id)
    memory_type = req.memory_type or "episodic"

    memory = service.store(
        coordinate=coord,
        payload=req.payload,
        memory_type=memory_type,
        tenant=tenant,
        embedding=req.embedding,
    )

    embedding_source = (memory.metadata or {}).get("embedding_source", "hash")
    return MemoryStoreResponse(
        coord=req.coord,
        memory_type=memory_type,
        embedding_source=str(embedding_source),
    )


@router.get("/{coord}", response=MemoryGetResponse, auth=StandaloneAuth())
def fetch_memory(
    request: HttpRequest, coord: str, tenant_id: str | None = None
) -> MemoryGetResponse:
    """Fetch a memory by coordinate using Django ORM."""
    ensure_permission(request, "read")
    service = _get_service()
    ensure_namespace_access(request, service.namespace)

    parsed = safe_parse_coord(coord)
    tenant = get_tenant_from_request(request, explicit_tenant=tenant_id)

    record = service.retrieve(parsed, tenant=tenant)
    if not record:
        raise HttpError(404, get_message(ErrorCode.MEMORY_NOT_FOUND))

    return MemoryGetResponse(memory=record)


@router.delete("/{coord}", response=MemoryDeleteResponse, auth=StandaloneAuth())
def delete_memory(
    request: HttpRequest, coord: str, tenant_id: str | None = None
) -> MemoryDeleteResponse:
    """Soft-delete a memory by coordinate using Django ORM."""
    ensure_permission(request, "delete")
    service = _get_service()
    ensure_namespace_access(request, service.namespace)

    parsed = safe_parse_coord(coord)
    tenant = get_tenant_from_request(request, explicit_tenant=tenant_id)

    deleted = service.delete(parsed, tenant=tenant)

    return MemoryDeleteResponse(coord=coord, deleted=deleted)
