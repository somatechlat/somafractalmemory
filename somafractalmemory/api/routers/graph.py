"""Graph routes - 100% Django + Django Ninja + Django ORM.

All database access through Django ORM models.
All strings use centralized messages for i18n.
"""

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from somafractalmemory.apps.aaas.auth import MultiAuth, can_access_namespace, has_permission
from somafractalmemory.apps.common.messages import ErrorCode, get_message
from somafractalmemory.apps.common.utils.logger import get_logger

from ..schemas import (
    GraphLinkRequest,
    GraphLinkResponse,
    GraphNeighborsResponse,
    GraphPathResponse,
)

logger = get_logger(__name__)
router = Router(tags=["graph"])


def _get_graph_service():
    """Get the graph service instance."""
    from somafractalmemory.api.core import get_graph

    return get_graph()


def _safe_parse_coord(coord: str) -> tuple[float, ...]:
    """Parse coordinate string to tuple of floats."""
    try:
        parts = [p.strip() for p in coord.split(",") if p.strip()]
        if not parts:
            raise HttpError(400, get_message(ErrorCode.EMPTY_COORDINATE))
        return tuple(float(p) for p in parts)
    except ValueError as exc:
        raise HttpError(400, get_message(ErrorCode.INVALID_COORDINATE, coord=coord)) from exc


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
    from somafractalmemory.api.core import get_graph

    namespace = get_graph().namespace
    if not can_access_namespace(request, namespace):
        raise HttpError(403, get_message(ErrorCode.PERMISSION_DENIED))


@router.post("/link", response=GraphLinkResponse, auth=MultiAuth())
def create_graph_link(request: HttpRequest, req: GraphLinkRequest) -> GraphLinkResponse:
    """Create a link between two memory coordinates using Django ORM."""
    _ensure_permission(request, "write")
    _ensure_namespace_access(request)

    service = _get_graph_service()
    tenant = _get_tenant_from_request(request)

    from_parsed = _safe_parse_coord(req.from_coord)
    to_parsed = _safe_parse_coord(req.to_coord)
    link_type = req.link_type or "related"

    link_data = {
        "link_type": link_type,
        "strength": req.strength,
        "_tenant": tenant,
    }
    if req.metadata:
        link_data.update(req.metadata)

    try:
        service.add_link(from_parsed, to_parsed, link_data)
        return GraphLinkResponse(
            from_coord=req.from_coord,
            to_coord=req.to_coord,
            link_type=link_type,
            ok=True,
        )
    except Exception as exc:
        logger.error("Graph link creation failed", error=str(exc), exc_info=True)
        raise HttpError(500, get_message(ErrorCode.GRAPH_LINK_FAILED)) from exc


@router.get("/neighbors", response=GraphNeighborsResponse, auth=MultiAuth())
def get_graph_neighbors(
    request: HttpRequest,
    coord: str,
    k_hop: int = 1,
    limit: int = 10,
    link_type: str | None = None,
) -> GraphNeighborsResponse:
    """Get neighbors of a coordinate using Django ORM."""
    _ensure_permission(request, "read")
    _ensure_namespace_access(request)

    service = _get_graph_service()
    tenant = _get_tenant_from_request(request)

    parsed = _safe_parse_coord(coord)

    try:
        neighbors = service.get_neighbors(parsed, link_type=link_type, limit=limit, tenant=tenant)

        clean_neighbors = [{k: v for k, v in n.items() if not k.startswith("_")} for n in neighbors]

        return GraphNeighborsResponse(coord=coord, neighbors=clean_neighbors)
    except Exception as exc:
        logger.error("Graph neighbors query failed", error=str(exc), exc_info=True)
        raise HttpError(500, get_message(ErrorCode.GRAPH_NEIGHBORS_FAILED)) from exc


@router.get("/path", response=GraphPathResponse, auth=MultiAuth())
def find_graph_path(
    request: HttpRequest,
    from_coord: str,
    to_coord: str,
    max_length: int = 10,
    link_type: str | None = None,
) -> GraphPathResponse:
    """Find the shortest path between two coordinates using Django ORM."""
    _ensure_permission(request, "read")
    _ensure_namespace_access(request)

    service = _get_graph_service()
    tenant = _get_tenant_from_request(request)

    from_parsed = _safe_parse_coord(from_coord)
    to_parsed = _safe_parse_coord(to_coord)

    try:
        path_result = service.find_shortest_path(
            from_parsed, to_parsed, link_type=link_type, tenant=tenant
        )

        if not path_result or len(path_result) > max_length:
            return GraphPathResponse(
                from_coord=from_coord,
                to_coord=to_coord,
                path=[],
                link_types=[],
                found=False,
            )

        path_strs = [",".join(str(c) for c in coord) for coord in path_result]

        return GraphPathResponse(
            from_coord=from_coord,
            to_coord=to_coord,
            path=path_strs,
            link_types=[link_type or "unknown"] * (len(path_result) - 1),
            found=True,
        )
    except Exception as exc:
        logger.error("Graph path query failed", error=str(exc), exc_info=True)
        return GraphPathResponse(
            from_coord=from_coord,
            to_coord=to_coord,
            path=[],
            link_types=[],
            found=False,
        )
