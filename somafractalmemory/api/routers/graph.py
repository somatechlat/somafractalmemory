"""Graph routes - 100% Django + Django Ninja + Django ORM.

All database access through Django ORM models.
All strings use centralized messages for i18n.
Auth via standalone facade — zero Soma Platform dependency.
"""

from django.http import HttpRequest
from ninja import Query, Router
from ninja.errors import HttpError

from somafractalmemory.admin.common.messages import ErrorCode, get_message
from somafractalmemory.admin.common.utils.logger import get_logger
from somafractalmemory.api.auth import StandaloneAuth
from somafractalmemory.api.utils import (
    ensure_namespace_access,
    ensure_permission,
    get_tenant_from_request,
    safe_parse_coord,
)

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


@router.post("/link", response=GraphLinkResponse, auth=StandaloneAuth())
def create_graph_link(request: HttpRequest, req: GraphLinkRequest) -> GraphLinkResponse:
    """Create a link between two memory coordinates using Django ORM."""
    ensure_permission(request, "write")
    service = _get_graph_service()
    ensure_namespace_access(request, service.namespace)

    tenant = get_tenant_from_request(request)

    from_parsed = safe_parse_coord(req.from_coord)
    to_parsed = safe_parse_coord(req.to_coord)
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
        logger.error("Graph link creation failed: %s", exc, exc_info=True)
        raise HttpError(500, get_message(ErrorCode.GRAPH_LINK_FAILED)) from exc


@router.get("/neighbors", response=GraphNeighborsResponse, auth=StandaloneAuth())
def get_graph_neighbors(
    request: HttpRequest,
    coord: str,
    # B18: k_hop is a real traversal depth, bounded to [1, 5]. An unbounded
    # depth turns one request into a full-graph walk.
    k_hop: int = Query(1, ge=1, le=5),
    # Bounded like somabrain MemoryRecallRequest.top_k (Field(3, ge=1, le=50))
    # and MemorySearchRequest.top_k (Field(5, ge=1, le=200)) — an unbounded
    # page size lets one request pull an entire adjacency set into a response.
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
    link_type: str | None = None,
) -> GraphNeighborsResponse:
    """Get neighbours within ``k_hop`` hops of a coordinate.

    Supports pagination with offset parameter. Each neighbour carries
    ``hops`` — the distance from the seed — so k_hop is honest (B18).
    """
    ensure_permission(request, "read")
    service = _get_graph_service()
    ensure_namespace_access(request, service.namespace)

    tenant = get_tenant_from_request(request)

    parsed = safe_parse_coord(coord)

    try:
        neighbors = service.get_neighbors(
            parsed,
            link_type=link_type,
            limit=limit,
            offset=offset,
            tenant=tenant,
            k_hop=k_hop,
        )

        clean_neighbors = [{k: v for k, v in n.items() if not k.startswith("_")} for n in neighbors]

        return GraphNeighborsResponse(coord=coord, neighbors=clean_neighbors)
    except Exception as exc:
        logger.error("Graph neighbors query failed: %s", exc, exc_info=True)
        raise HttpError(500, get_message(ErrorCode.GRAPH_NEIGHBORS_FAILED)) from exc


@router.get("/path", response=GraphPathResponse, auth=StandaloneAuth())
def find_graph_path(
    request: HttpRequest,
    from_coord: str,
    to_coord: str,
    max_length: int = 10,
    link_type: str | None = None,
) -> GraphPathResponse:
    """Find the shortest path between two coordinates using Django ORM."""
    ensure_permission(request, "read")
    service = _get_graph_service()
    ensure_namespace_access(request, service.namespace)

    tenant = get_tenant_from_request(request)

    from_parsed = safe_parse_coord(from_coord)
    to_parsed = safe_parse_coord(to_coord)

    try:
        path_result = service.find_shortest_path(
            from_parsed, to_parsed, link_type=link_type, tenant=tenant, max_depth=max_length
        )

        if not path_result or len(path_result) > max_length:
            # Legitimate empty answer: the store answered and there is no path.
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
            link_types=[link_type or "related"] * (len(path_result) - 1),
            found=True,
        )
    except Exception as exc:
        # D8: an exception is not "no path exists". found=False alone would
        # tell the caller the graph has no path; the store actually could not
        # answer. Flag it (law 5: degraded recall must never look like an
        # honest empty result).
        logger.error("Graph path query failed: %s", exc, exc_info=True)
        return GraphPathResponse(
            from_coord=from_coord,
            to_coord=to_coord,
            path=[],
            link_types=[],
            found=False,
            degraded=True,
            degraded_reason=str(exc),
        )
