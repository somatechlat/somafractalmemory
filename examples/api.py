"""
Minimal FastAPI example exposing store/recall/stats endpoints.

Run (after installing fastapi and uvicorn):
  pip install fastapi uvicorn
  uvicorn examples.api:app --reload
"""

# Clean up and organize imports
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def parse_coord(text: str) -> Tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


app = FastAPI(title="SomaFractalMemory API")


# Generate a static OpenAPI JSON file on startup so docs can reference it.
@app.on_event("startup")
def _write_openapi() -> None:
    import json
    import pathlib

    spec = app.openapi()
    root = pathlib.Path(__file__).resolve().parents[1]
    (root / "openapi.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print("✅ openapi.json generated at", root / "openapi.json")


mem = create_memory_system(
    MemoryMode.DEVELOPMENT,
    "api_ns",
    config={"redis": {"testing": True}, "qdrant": {"path": "./qdrant.db"}},
)

# Simple auth + rate limit stubs
API_TOKEN = os.getenv("SOMA_API_TOKEN")
_RATE: dict[tuple[str, str], list[float]] = {}


def auth_dep(authorization: str | None = Header(default=None)):
    if API_TOKEN:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1]
        if token != API_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")


def rate_limit_dep(path: str):
    # Allow up to 60 requests per minute per path
    window = 60.0
    max_reqs = 60
    key = (path, "global")
    now = time.time()
    bucket = _RATE.setdefault(key, [])
    # Drop old
    while bucket and now - bucket[0] > window:
        bucket.pop(0)
    if len(bucket) >= max_reqs:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)


class StoreRequest(BaseModel):
    coord: str
    payload: Dict[str, Any]
    type: Optional[str] = "episodic"


class RecallRequest(BaseModel):
    query: str
    top_k: int = 5
    type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class ExportMemoriesRequest(BaseModel):
    path: str


class ImportMemoriesRequest(BaseModel):
    path: str
    replace: bool = False


class DeleteManyRequest(BaseModel):
    coords: list[str]


class LinkRequest(BaseModel):
    from_coord: str
    to_coord: str
    type: str = "related"
    weight: float = 1.0


class BulkItem(BaseModel):
    coord: str
    payload: dict
    type: str = "episodic"


class StoreBulkRequest(BaseModel):
    items: list[BulkItem]


class RecallBatchRequest(BaseModel):
    queries: list[str]
    top_k: int = 5
    type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


# --- Response models ---
class OkResponse(BaseModel):
    ok: bool


class MatchesResponse(BaseModel):
    matches: List[Dict[str, Any]]


class BatchesResponse(BaseModel):
    batches: List[List[Dict[str, Any]]]


class ScoreItem(BaseModel):
    payload: Dict[str, Any]
    score: Optional[float] = None


class ScoresResponse(BaseModel):
    results: List[ScoreItem]


class ResultsResponse(BaseModel):
    results: List[Dict[str, Any]]


class NeighborsResponse(BaseModel):
    # Preserve shape: [[coord:list[float], edge_data:dict], ...]
    neighbors: List[List[Any]]


class PathResponse(BaseModel):
    path: List[List[float]]


class ExportMemoriesResponse(BaseModel):
    exported: int


class ImportMemoriesResponse(BaseModel):
    imported: int


class DeleteManyResponse(BaseModel):
    deleted: int


class StoreBulkResponse(BaseModel):
    stored: int


class StatsResponse(BaseModel):
    total_memories: int
    episodic: int
    semantic: int


class HealthResponse(BaseModel):
    kv_store: bool
    vector_store: bool
    graph_store: bool
    prediction_provider: bool


# Prometheus metrics for API operations
API_REQUESTS = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["endpoint", "method"],
)
API_LATENCY = Histogram(
    "api_request_latency_seconds",
    "Latency of API requests in seconds",
    ["endpoint", "method"],
)


# Helper decorator to instrument endpoints
def instrument(endpoint_name: str, method: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            API_REQUESTS.labels(endpoint=endpoint_name, method=method).inc()
            with API_LATENCY.labels(endpoint=endpoint_name, method=method).time():
                return await func(*args, **kwargs)

        return wrapper

    return decorator


@app.post(
    "/store",
    response_model=OkResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/store"))],
)
@instrument(endpoint_name="store", method="POST")
async def store(req: StoreRequest) -> OkResponse:
    mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    mem.store_memory(parse_coord(req.coord), req.payload, memory_type=mtype)
    return OkResponse(ok=True)


@app.post(
    "/recall",
    response_model=MatchesResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall"))],
)
@instrument(endpoint_name="recall", method="POST")
async def recall(req: RecallRequest) -> MatchesResponse:
    mtype = None
    if req.type:
        mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    if req.filters:
        res = mem.find_hybrid_by_type(
            req.query, top_k=req.top_k, memory_type=mtype, filters=req.filters
        )
    else:
        res = mem.recall(req.query, top_k=req.top_k, memory_type=mtype)
    return MatchesResponse(matches=res)


@app.post(
    "/recall_batch",
    response_model=BatchesResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall_batch"))],
)
def recall_batch(req: RecallBatchRequest) -> BatchesResponse:
    mtype = None
    if req.type:
        mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    res = mem.recall_batch(req.queries, top_k=req.top_k, memory_type=mtype, filters=req.filters)
    return BatchesResponse(batches=res)


@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["system"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/stats"))],
)
def stats() -> StatsResponse:
    return StatsResponse(**mem.memory_stats())


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(**mem.health_check())


@app.get(
    "/neighbors",
    response_model=NeighborsResponse,
    tags=["graph"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/neighbors"))],
)
def neighbors(
    coord: str, link_type: str | None = None, limit: int | None = None
) -> NeighborsResponse:
    c = parse_coord(coord)
    nbrs = mem.graph_store.get_neighbors(c, link_type=link_type, limit=limit)
    # Convert coords to lists for JSON
    return NeighborsResponse(neighbors=[[list(co), data] for co, data in nbrs])


@app.post(
    "/export_memories",
    response_model=ExportMemoriesResponse,
    tags=["admin"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/export_memories"))],
)
def export_memories(req: ExportMemoriesRequest) -> ExportMemoriesResponse:
    n = mem.export_memories(req.path)
    return ExportMemoriesResponse(exported=n)


@app.post(
    "/import_memories",
    response_model=ImportMemoriesResponse,
    tags=["admin"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/import_memories"))],
)
def import_memories(req: ImportMemoriesRequest) -> ImportMemoriesResponse:
    n = mem.import_memories(req.path, replace=req.replace)
    return ImportMemoriesResponse(imported=n)


@app.post(
    "/delete_many",
    response_model=DeleteManyResponse,
    tags=["admin"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/delete_many"))],
)
def delete_many(req: DeleteManyRequest) -> DeleteManyResponse:
    coords = [parse_coord(s) for s in req.coords]
    n = mem.delete_many(coords)
    return DeleteManyResponse(deleted=n)


@app.post(
    "/link",
    response_model=OkResponse,
    tags=["graph"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/link"))],
)
def link(req: LinkRequest) -> OkResponse:
    mem.link_memories(
        parse_coord(req.from_coord),
        parse_coord(req.to_coord),
        link_type=req.type,
        weight=req.weight,
    )
    return OkResponse(ok=True)


@app.get(
    "/shortest_path",
    response_model=PathResponse,
    tags=["graph"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/shortest_path"))],
)
def shortest_path(frm: str, to: str, link_type: str | None = None) -> PathResponse:
    path = mem.find_shortest_path(parse_coord(frm), parse_coord(to), link_type=link_type)
    return PathResponse(path=[list(c) for c in path])


@app.post(
    "/store_bulk",
    response_model=StoreBulkResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/store_bulk"))],
)
def store_bulk(req: StoreBulkRequest) -> StoreBulkResponse:
    from somafractalmemory.core import MemoryType

    items = []
    for it in req.items:
        mtype = MemoryType.SEMANTIC if it.type == "semantic" else MemoryType.EPISODIC
        items.append((parse_coord(it.coord), it.payload, mtype))
    mem.store_memories_bulk(items)
    return StoreBulkResponse(stored=len(items))


@app.post(
    "/recall_with_scores",
    response_model=ScoresResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall_with_scores"))],
)
def recall_with_scores(query: str, top_k: int = 5, type: str | None = None) -> ScoresResponse:
    from somafractalmemory.core import MemoryType

    mtype = (
        MemoryType.SEMANTIC
        if type == "semantic"
        else (MemoryType.EPISODIC if type == "episodic" else None)
    )
    res = mem.recall_with_scores(query, top_k=top_k, memory_type=mtype)
    return ScoresResponse(results=res)


@app.post(
    "/recall_with_context",
    response_model=ResultsResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall_with_context"))],
)
def recall_with_context(
    query: str, context: dict, top_k: int = 5, type: str | None = None
) -> ResultsResponse:
    from somafractalmemory.core import MemoryType

    mtype = (
        MemoryType.SEMANTIC
        if type == "semantic"
        else (MemoryType.EPISODIC if type == "episodic" else None)
    )
    res = mem.find_hybrid_with_context(query, context, top_k=top_k, memory_type=mtype)
    return ResultsResponse(results=res)


@app.get(
    "/range",
    response_model=Dict[str, List[List[float]]],
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/range"))],
)
def range_search(min: str, max: str, type: str | None = None):
    from somafractalmemory.core import MemoryType

    mtype = (
        MemoryType.SEMANTIC
        if type == "semantic"
        else (MemoryType.EPISODIC if type == "episodic" else None)
    )
    mi = parse_coord(min)
    ma = parse_coord(max)
    res = mem.find_by_coordinate_range(mi, ma, memory_type=mtype)
    return {"coords": [m.get("coordinate") for m in res if m.get("coordinate")]}


@app.get(
    "/metrics",
    include_in_schema=False,
)
def metrics() -> Response:
    """Expose Prometheus metrics for the FastAPI server."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
