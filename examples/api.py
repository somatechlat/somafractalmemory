"""
Minimal FastAPI example exposing store/recall/stats endpoints.

Run (after installing fastapi and uvicorn):
  pip install fastapi uvicorn
  uvicorn examples.api:app --reload
"""

import os
import time
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def parse_coord(text: str) -> tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


# Set up a basic tracer provider with console exporter
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

app = FastAPI(title="SomaFractalMemory API")
# Instrument the FastAPI app for tracing
FastAPIInstrumentor().instrument_app(app)


def _resolve_memory_mode() -> MemoryMode:
    mode_env = (os.getenv("MEMORY_MODE") or MemoryMode.DEVELOPMENT.value).lower()
    for mode in MemoryMode:
        if mode.value == mode_env:
            return mode
    return MemoryMode.DEVELOPMENT


def _redis_config() -> dict[str, Any]:
    cfg: dict[str, Any] = {"testing": False}
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        parsed = urlparse(redis_url)
        if parsed.hostname:
            cfg["host"] = parsed.hostname
        if parsed.port:
            cfg["port"] = parsed.port
        path = parsed.path.lstrip("/")
        if path.isdigit():
            cfg["db"] = int(path)
    if host := os.getenv("REDIS_HOST"):
        cfg["host"] = host
    if port := os.getenv("REDIS_PORT"):
        try:
            cfg["port"] = int(port)
        except ValueError:
            pass
    if db := os.getenv("REDIS_DB"):
        try:
            cfg["db"] = int(db)
        except ValueError:
            pass
    return cfg


def _qdrant_config() -> dict[str, Any]:
    url = os.getenv("QDRANT_URL")
    if url:
        return {"url": url}
    host = os.getenv("QDRANT_HOST", "qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return {"host": host, "port": port}


memory_mode = _resolve_memory_mode()
config: dict[str, Any] = {
    "postgres": {"url": os.getenv("POSTGRES_URL")},
    "vector": {"backend": "qdrant"},
    "qdrant": _qdrant_config(),
}

redis_cfg = _redis_config()
if redis_cfg:
    config["redis"] = redis_cfg

eventing_env = os.getenv("EVENTING_ENABLED")
if eventing_env is not None:
    config["eventing"] = {"enabled": eventing_env.lower() in ("1", "true", "yes", "on")}

mem = create_memory_system(memory_mode, os.getenv("SOMA_MEMORY_NAMESPACE", "api_ns"), config=config)
print("[DEBUG] Memory mode:", memory_mode.value)
print("[DEBUG] POSTGRES_URL used:", os.getenv("POSTGRES_URL"))
if redis_host := redis_cfg.get("host"):
    print("[DEBUG] Redis host:", redis_host)
if qdrant_url := config["qdrant"].get("url"):
    print("[DEBUG] Qdrant URL:", qdrant_url)
else:
    print("[DEBUG] Qdrant host:", config["qdrant"].get("host"))

# Some tests expect a prediction_provider attribute for health endpoints; provide a no-op stub
if not hasattr(mem, "prediction_provider"):

    class _NoopPredictor:
        def health_check(self):
            return True

    mem.prediction_provider = _NoopPredictor()  # type: ignore[attr-defined]


# Simple auth + rate limit stubs
API_TOKEN = os.getenv("SOMA_API_TOKEN")
_RATE: dict[tuple[str, str], list[float]] = {}
_RATE_LIMIT_MAX = int(os.getenv("SOMA_RATE_LIMIT_MAX", "60"))
_RATE_WINDOW = float(os.getenv("SOMA_RATE_LIMIT_WINDOW_SECONDS", "60"))


def auth_dep(request: Request):  # noqa: B008 - FastAPI dependency signature
    """Extract Authorization header manually to avoid Header call in defaults.

    FastAPI recommends using ``Header`` for dependency injection, but the linter
    flags calling it in a default argument. This implementation reads the header
    from the ``Request`` object directly, preserving the same security checks.
    """
    if API_TOKEN:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1]
        if token != API_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")


def rate_limit_dep(path: str):
    window = _RATE_WINDOW if _RATE_WINDOW > 0 else 60.0
    max_reqs = max(_RATE_LIMIT_MAX, 1)
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
    payload: dict[str, Any]
    type: str | None = "episodic"


class RecallRequest(BaseModel):
    query: str
    top_k: int = 5
    type: str | None = None
    filters: dict[str, Any] | None = None


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
    type: str | None = None
    filters: dict[str, Any] | None = None


# --- Response models ---
class OkResponse(BaseModel):
    ok: bool


class MatchesResponse(BaseModel):
    matches: list[dict[str, Any]]


class BatchesResponse(BaseModel):
    batches: list[list[dict[str, Any]]]


class ScoreItem(BaseModel):
    payload: dict[str, Any]
    score: float | None = None


class ScoresResponse(BaseModel):
    results: list[ScoreItem]


class ResultsResponse(BaseModel):
    results: list[dict[str, Any]]


class NeighborsResponse(BaseModel):
    # Preserve shape: [[coord:list[float], edge_data:dict], ...]
    neighbors: list[list[Any]]


class PathResponse(BaseModel):
    path: list[list[float]]


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
    # Some memory system implementations don't provide a recall_batch helper.
    # Fall back to calling recall/find_hybrid_by_type per query to maintain
    # compatibility across implementations.
    batches: list[list[dict[str, Any]]] = []
    for q in req.queries:
        if req.filters:
            batch = mem.find_hybrid_by_type(
                q, top_k=req.top_k, memory_type=mtype, filters=req.filters
            )
        else:
            batch = mem.recall(q, top_k=req.top_k, memory_type=mtype)
        batches.append(batch)
    return BatchesResponse(batches=batches)


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
) -> ResultsResponse:  # noqa: F811 – suppress redefinition warning if any
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
    response_model=dict[str, list[list[float]]],
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


# Root endpoint that points users to the metrics URL
@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "SomaFractalMemory API is running", "metrics": "/metrics"}


# ------------------------------------------------------------
# 404 Not Found metrics
# ------------------------------------------------------------
HTTP_404_REQUESTS = Counter(
    "http_404_requests_total",
    "Total number of HTTP 404 (Not Found) responses",
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        HTTP_404_REQUESTS.inc()
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    # For other errors, let FastAPI handle them
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Health and readiness endpoints
@app.get("/healthz", response_model=HealthResponse)
def healthz():
    """Liveness probe – checks basic health of all stores and prediction provider."""
    return HealthResponse(
        kv_store=mem.kv_store.health_check(),
        vector_store=mem.vector_store.health_check(),
        graph_store=mem.graph_store.health_check(),
        prediction_provider=mem.prediction_provider.health_check(),
    )


@app.get("/readyz", response_model=HealthResponse)
def readyz():
    """Readiness probe – same checks for now; can be extended with more strict criteria later."""
    return HealthResponse(
        kv_store=mem.kv_store.health_check(),
        vector_store=mem.vector_store.health_check(),
        graph_store=mem.graph_store.health_check(),
        prediction_provider=mem.prediction_provider.health_check(),
    )
