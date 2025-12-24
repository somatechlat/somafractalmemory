"""Memory CRUD routes - 100% Django + Django Ninja + Django ORM.

All database access through Django ORM models.
All strings use centralized messages for i18n.
"""

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from common.utils.logger import get_logger

from ..messages import ErrorCode, get_message
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


def _safe_parse_coord(coord: str) -> tuple[float, ...]:
    """Parse coordinate string to tuple of floats."""
    try:
        parts = [p.strip() for p in coord.split(",") if p.strip()]
        if not parts:
            raise HttpError(400, get_message(ErrorCode.EMPTY_COORDINATE))
        return tuple(float(p) for p in parts)
    except ValueError:
        raise HttpError(400, get_message(ErrorCode.INVALID_COORDINATE, coord=coord))


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


@router.post("", response=MemoryStoreResponse)
def store_memory(request: HttpRequest, req: MemoryStoreRequest) -> MemoryStoreResponse:
    """Store a memory using Django ORM."""
    _check_auth(request)

    service = _get_service()
    coord = _safe_parse_coord(req.coord)
    tenant = _get_tenant_from_request(request)
    memory_type = req.memory_type or "episodic"

    service.store(
        coordinate=coord,
        payload=req.payload,
        memory_type=memory_type,
        tenant=tenant,
    )

    return MemoryStoreResponse(coord=req.coord, memory_type=memory_type)


@router.get("/{coord}", response=MemoryGetResponse)
def fetch_memory(request: HttpRequest, coord: str) -> MemoryGetResponse:
    """Fetch a memory by coordinate using Django ORM."""
    _check_auth(request)

    service = _get_service()
    parsed = _safe_parse_coord(coord)
    tenant = _get_tenant_from_request(request)

    record = service.retrieve(parsed, tenant=tenant)
    if not record:
        raise HttpError(404, get_message(ErrorCode.MEMORY_NOT_FOUND))

    return MemoryGetResponse(memory=record)


@router.delete("/{coord}", response=MemoryDeleteResponse)
def delete_memory(request: HttpRequest, coord: str) -> MemoryDeleteResponse:
    """Delete a memory using Django ORM."""
    _check_auth(request)

    service = _get_service()
    parsed = _safe_parse_coord(coord)
    tenant = _get_tenant_from_request(request)

    deleted = service.delete(parsed, tenant=tenant)

    return MemoryDeleteResponse(coord=coord, deleted=deleted)
