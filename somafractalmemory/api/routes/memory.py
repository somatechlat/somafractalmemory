# somafractalmemory/api/routes/memory.py
"""Memory CRUD routes for SomaFractalMemory API.

Extracted from http_api.py for VIBE compliance (<500 lines per file).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from opentelemetry import trace

from common.utils.logger import get_logger
from somafractalmemory.core import DeleteError, KeyValueStoreError, VectorStoreError

from ..dependencies import (
    auth_dep,
    get_tenant_from_request,
    rate_limit_dep,
    resolve_memory_type,
    safe_parse_coord,
)
from ..schemas import (
    MemoryDeleteResponse,
    MemoryGetResponse,
    MemoryStoreRequest,
    MemoryStoreResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/memories", tags=["memories"])


def get_mem():
    """Get the memory system instance. Imported at runtime to avoid circular imports."""
    from somafractalmemory.http_api import mem

    return mem


@router.post(
    "",
    response_model=MemoryStoreResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.store"))],
)
async def store_memory(req: MemoryStoreRequest, request: Request = None) -> MemoryStoreResponse:
    """Store a memory."""
    mem = get_mem()
    memory_type = resolve_memory_type(req.memory_type)
    coord = safe_parse_coord(req.coord)
    tenant = get_tenant_from_request(request) if request else "default"

    memory_data = {
        "payload": req.payload,
        "_tenant": tenant,
    }
    mem.store_memory(coord, memory_data, memory_type=memory_type)
    return MemoryStoreResponse(coord=req.coord, memory_type=memory_type.value)


@router.get(
    "/{coord}",
    response_model=MemoryGetResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.fetch"))],
)
def fetch_memory(coord: str, request: Request = None) -> MemoryGetResponse:
    """Fetch a memory by coordinate."""
    mem = get_mem()
    try:
        parsed = safe_parse_coord(coord)
    except HTTPException:
        raise

    requesting_tenant = get_tenant_from_request(request) if request else "default"
    record = mem.retrieve(parsed)
    if not record:
        raise HTTPException(status_code=404, detail="Memory not found")

    stored_tenant = record.get("_tenant", "default")
    if stored_tenant != requesting_tenant:
        logger.warning(
            "Tenant isolation: access denied",
            requesting_tenant=requesting_tenant,
            stored_tenant=stored_tenant,
            coord=coord,
        )
        raise HTTPException(status_code=404, detail="Memory not found")

    response_record = {k: v for k, v in record.items() if not k.startswith("_")}

    if not response_record.get("payload"):
        try:
            for point in mem.vector_store.scroll():
                pt_payload = getattr(point, "payload", {})
                if isinstance(pt_payload, dict) and pt_payload.get("coordinate") == list(parsed):
                    if pt_payload.get("_tenant", "default") == requesting_tenant:
                        response_record["payload"] = pt_payload.get("payload", {})
                        break
        except Exception:
            pass
    return MemoryGetResponse(memory=response_record)


@router.delete(
    "/{coord}",
    response_model=MemoryDeleteResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.delete"))],
)
def delete_memory(coord: str, request: Request = None) -> MemoryDeleteResponse:
    """Delete a memory."""
    mem = get_mem()
    try:
        parsed = safe_parse_coord(coord)
    except HTTPException:
        raise

    tracer = trace.get_tracer("soma.http_api")
    with tracer.start_as_current_span("delete_memory") as span:
        try:
            deleted = mem.delete(parsed)
            return MemoryDeleteResponse(coord=coord, deleted=bool(deleted))
        except VectorStoreError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error("Vector store delete error", error=str(exc), exc_info=True)
            raise HTTPException(status_code=502, detail="Vector store error during delete") from exc
        except KeyValueStoreError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error("KV delete error", error=str(exc), exc_info=True)
            raise HTTPException(
                status_code=500, detail="Key-value store error during delete"
            ) from exc
        except DeleteError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error("Delete operation failed", error=str(exc), exc_info=True)
            raise HTTPException(status_code=500, detail="Delete operation failed") from exc
