# somafractalmemory/api/routes/graph.py
"""Graph route handlers for SomaFractalMemory API.

Extracted from http_api.py for VIBE compliance (<500 lines per file).
"""

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from opentelemetry import trace
from prometheus_client import Counter, Histogram

from ..dependencies import auth_dep, get_tenant_from_request, rate_limit_dep, safe_parse_coord
from ..schemas import (
    GraphLinkRequest,
    GraphLinkResponse,
    GraphNeighborsResponse,
    GraphPathResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/graph", tags=["graph"])


def get_mem():
    """Get the memory system instance. Imported at runtime to avoid circular imports."""
    from somafractalmemory.http_api import mem

    return mem


def _maybe_submit(fn):
    """Submit metric update, falling back to sync if async unavailable."""
    from common.config.settings import load_settings
    from common.utils.async_metrics import submit as _submit_metric

    _settings = load_settings()
    if _settings.async_metrics_enabled:
        try:
            _submit_metric(fn)
            return
        except Exception:
            pass
    try:
        fn()
    except Exception:
        pass


# Prometheus metrics for graph operations
GRAPH_LINK_TOTAL = Counter(
    "sfm_graph_link_total",
    "Total graph link creation operations",
    ["tenant", "link_type", "status"],
)
GRAPH_LINK_LATENCY = Histogram(
    "sfm_graph_link_latency_seconds",
    "Graph link creation latency",
    ["tenant", "link_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
GRAPH_NEIGHBORS_TOTAL = Counter(
    "sfm_graph_neighbors_total",
    "Total graph neighbors query operations",
    ["tenant", "status"],
)
GRAPH_NEIGHBORS_LATENCY = Histogram(
    "sfm_graph_neighbors_latency_seconds",
    "Graph neighbors query latency",
    ["tenant"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
GRAPH_PATH_TOTAL = Counter(
    "sfm_graph_path_total",
    "Total graph path query operations",
    ["tenant", "status", "found"],
)
GRAPH_PATH_LATENCY = Histogram(
    "sfm_graph_path_latency_seconds",
    "Graph path query latency",
    ["tenant"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)


@router.post(
    "/link",
    response_model=GraphLinkResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/graph.link"))],
)
def create_graph_link(req: GraphLinkRequest, request: Request = None) -> GraphLinkResponse:
    """Create a link between two memory coordinates in the graph store.

    TENANT ISOLATION: Links are scoped by tenant extracted from request headers.
    """
    mem = get_mem()
    tenant = get_tenant_from_request(request) if request else "default"
    link_type = req.link_type or "related"

    tracer = trace.get_tracer("soma.http_api")
    with tracer.start_as_current_span("graph_link_create") as span:
        span.set_attribute("tenant", tenant)
        span.set_attribute("link_type", link_type)
        start_time = time.perf_counter()

        try:
            from_parsed = safe_parse_coord(req.from_coord)
            to_parsed = safe_parse_coord(req.to_coord)
        except HTTPException:
            _maybe_submit(
                lambda: GRAPH_LINK_TOTAL.labels(
                    tenant=tenant, link_type=link_type, status="error"
                ).inc()
            )
            raise

        span.set_attribute("from_coord", req.from_coord)
        span.set_attribute("to_coord", req.to_coord)

        link_data = {
            "link_type": link_type,
            "strength": req.strength,
            "_tenant": tenant,
            "created_at": time.time(),
        }
        if req.metadata:
            link_data.update(req.metadata)

        try:
            mem.graph_store.add_link(from_parsed, to_parsed, link_data)
            duration = time.perf_counter() - start_time
            _maybe_submit(
                lambda: GRAPH_LINK_TOTAL.labels(
                    tenant=tenant, link_type=link_type, status="success"
                ).inc()
            )
            _maybe_submit(
                lambda: GRAPH_LINK_LATENCY.labels(tenant=tenant, link_type=link_type).observe(
                    duration
                )
            )
            return GraphLinkResponse(
                from_coord=req.from_coord,
                to_coord=req.to_coord,
                link_type=link_type,
                ok=True,
            )
        except Exception as exc:
            duration = time.perf_counter() - start_time
            _maybe_submit(
                lambda: GRAPH_LINK_TOTAL.labels(
                    tenant=tenant, link_type=link_type, status="error"
                ).inc()
            )
            _maybe_submit(
                lambda: GRAPH_LINK_LATENCY.labels(tenant=tenant, link_type=link_type).observe(
                    duration
                )
            )
            span.record_exception(exc)
            logger.error("Graph link creation failed", error=str(exc), exc_info=True)
            raise HTTPException(status_code=500, detail="Graph link creation failed") from exc


@router.get(
    "/neighbors",
    response_model=GraphNeighborsResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/graph.neighbors"))],
)
def get_graph_neighbors(
    coord: str,
    k_hop: int = 1,
    limit: int = 10,
    link_type: str | None = None,
    request: Request = None,
) -> GraphNeighborsResponse:
    """Get neighbors of a coordinate in the graph store.

    TENANT ISOLATION: Results are filtered by tenant for isolation.
    """
    mem = get_mem()
    requesting_tenant = get_tenant_from_request(request) if request else "default"

    tracer = trace.get_tracer("soma.http_api")
    with tracer.start_as_current_span("graph_neighbors_query") as span:
        span.set_attribute("tenant", requesting_tenant)
        span.set_attribute("coord", coord)
        span.set_attribute("k_hop", k_hop)
        span.set_attribute("limit", limit)
        if link_type:
            span.set_attribute("link_type", link_type)
        start_time = time.perf_counter()

        try:
            parsed = safe_parse_coord(coord)
        except HTTPException:
            _maybe_submit(
                lambda: GRAPH_NEIGHBORS_TOTAL.labels(tenant=requesting_tenant, status="error").inc()
            )
            raise

        try:
            neighbors = mem.graph_store.get_neighbors(
                parsed,
                link_type=link_type,
                limit=limit * 2,
            )

            filtered_neighbors = []
            for neighbor in neighbors:
                neighbor_tenant = neighbor.get("_tenant", "default")
                if neighbor_tenant == requesting_tenant:
                    clean_neighbor = {k: v for k, v in neighbor.items() if not k.startswith("_")}
                    filtered_neighbors.append(clean_neighbor)
                    if len(filtered_neighbors) >= limit:
                        break

            duration = time.perf_counter() - start_time
            span.set_attribute("neighbors_count", len(filtered_neighbors))
            _maybe_submit(
                lambda: GRAPH_NEIGHBORS_TOTAL.labels(
                    tenant=requesting_tenant, status="success"
                ).inc()
            )
            _maybe_submit(
                lambda: GRAPH_NEIGHBORS_LATENCY.labels(tenant=requesting_tenant).observe(duration)
            )

            return GraphNeighborsResponse(coord=coord, neighbors=filtered_neighbors)
        except Exception as exc:
            duration = time.perf_counter() - start_time
            _maybe_submit(
                lambda: GRAPH_NEIGHBORS_TOTAL.labels(tenant=requesting_tenant, status="error").inc()
            )
            _maybe_submit(
                lambda: GRAPH_NEIGHBORS_LATENCY.labels(tenant=requesting_tenant).observe(duration)
            )
            span.record_exception(exc)
            logger.error("Graph neighbors query failed", error=str(exc), exc_info=True)
            raise HTTPException(status_code=500, detail="Graph neighbors query failed") from exc


@router.get(
    "/path",
    response_model=GraphPathResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/graph.path"))],
)
def find_graph_path(
    from_coord: str,
    to_coord: str,
    max_length: int = 10,
    link_type: str | None = None,
    request: Request = None,
) -> GraphPathResponse:
    """Find the shortest path between two coordinates in the graph.

    Returns empty path if no path exists (not an error).
    """
    mem = get_mem()
    requesting_tenant = get_tenant_from_request(request) if request else "default"

    tracer = trace.get_tracer("soma.http_api")
    with tracer.start_as_current_span("graph_path_query") as span:
        span.set_attribute("tenant", requesting_tenant)
        span.set_attribute("from_coord", from_coord)
        span.set_attribute("to_coord", to_coord)
        span.set_attribute("max_length", max_length)
        if link_type:
            span.set_attribute("link_type", link_type)
        start_time = time.perf_counter()

        try:
            from_parsed = safe_parse_coord(from_coord)
            to_parsed = safe_parse_coord(to_coord)
        except HTTPException:
            _maybe_submit(
                lambda: GRAPH_PATH_TOTAL.labels(
                    tenant=requesting_tenant, status="error", found="false"
                ).inc()
            )
            raise

        try:
            path_result = mem.graph_store.find_shortest_path(
                from_parsed, to_parsed, link_type=link_type
            )

            duration = time.perf_counter() - start_time

            if not path_result or len(path_result) > max_length:
                span.set_attribute("path_found", False)
                _maybe_submit(
                    lambda: GRAPH_PATH_TOTAL.labels(
                        tenant=requesting_tenant, status="success", found="false"
                    ).inc()
                )
                _maybe_submit(
                    lambda: GRAPH_PATH_LATENCY.labels(tenant=requesting_tenant).observe(duration)
                )
                return GraphPathResponse(
                    from_coord=from_coord,
                    to_coord=to_coord,
                    path=[],
                    link_types=[],
                    found=False,
                )

            path_strs = [",".join(str(c) for c in coord) for coord in path_result]

            link_types = []
            for i in range(len(path_result) - 1):
                try:
                    edge_data = mem.graph_store.graph.get_edge_data(
                        path_result[i], path_result[i + 1]
                    )
                    if edge_data:
                        link_types.append(edge_data.get("link_type", "unknown"))
                    else:
                        link_types.append("unknown")
                except Exception:
                    link_types.append("unknown")

            span.set_attribute("path_found", True)
            span.set_attribute("path_length", len(path_result))
            _maybe_submit(
                lambda: GRAPH_PATH_TOTAL.labels(
                    tenant=requesting_tenant, status="success", found="true"
                ).inc()
            )
            _maybe_submit(
                lambda: GRAPH_PATH_LATENCY.labels(tenant=requesting_tenant).observe(duration)
            )

            return GraphPathResponse(
                from_coord=from_coord,
                to_coord=to_coord,
                path=path_strs,
                link_types=link_types,
                found=True,
            )
        except Exception as exc:
            duration = time.perf_counter() - start_time
            _maybe_submit(
                lambda: GRAPH_PATH_TOTAL.labels(
                    tenant=requesting_tenant, status="error", found="false"
                ).inc()
            )
            _maybe_submit(
                lambda: GRAPH_PATH_LATENCY.labels(tenant=requesting_tenant).observe(duration)
            )
            span.record_exception(exc)
            logger.error("Graph path query failed", error=str(exc), exc_info=True)
            return GraphPathResponse(
                from_coord=from_coord,
                to_coord=to_coord,
                path=[],
                link_types=[],
                found=False,
            )
