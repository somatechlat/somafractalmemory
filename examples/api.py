"""
Minimal FastAPI example exposing store/recall/stats endpoints.

Run (after installing fastapi and uvicorn):
  pip install fastapi uvicorn
  uvicorn examples.api:app --reload
"""

import inspect
import os
import time
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
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


def parse_coord(text: str) -> Tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _redis_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        parsed = urlparse(redis_url)
        if parsed.hostname:
            cfg["host"] = parsed.hostname
        if parsed.port:
            cfg["port"] = parsed.port
        if parsed.path:
            path = parsed.path.lstrip("/")
            if path.isdigit():
                cfg["db"] = int(path)
    redis_host = os.getenv("REDIS_HOST")
    if redis_host:
        cfg["host"] = redis_host
    redis_port = os.getenv("REDIS_PORT")
    if redis_port:
        try:
            cfg["port"] = int(redis_port)
        except ValueError:
            pass
    redis_db = os.getenv("REDIS_DB")
    if redis_db:
        try:
            cfg["db"] = int(redis_db)
        except ValueError:
            pass
    cfg.setdefault("host", os.getenv("REDIS_FALLBACK_HOST", "redis"))
    cfg.setdefault("port", int(os.getenv("REDIS_FALLBACK_PORT", "6379")))
    cfg.setdefault("db", int(os.getenv("REDIS_FALLBACK_DB", "0")))
    return cfg


def _postgres_config() -> Dict[str, Any]:
    url = os.getenv("POSTGRES_URL")
    if url:
        return {"url": url}
    host = os.getenv("POSTGRES_HOST")
    if host:
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        database = os.getenv("POSTGRES_DB", "somamemory")
        return {"url": f"postgresql://{user}:{password}@{host}:{port}/{database}"}
    # Local fallback for ad-hoc testing
    return {"url": "postgresql://postgres:postgres@localhost:5432/somamemory"}


def _qdrant_config() -> Dict[str, Any]:
    url = os.getenv("QDRANT_URL")
    if url:
        return {"url": url}
    host = os.getenv("QDRANT_HOST", "qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return {"host": host, "port": port}


def _build_config(mode: MemoryMode) -> Dict[str, Any]:
    if mode in (MemoryMode.EVENTED_ENTERPRISE, MemoryMode.CLOUD_MANAGED):
        return {
            "redis": _redis_config(),
            "postgres": _postgres_config(),
            "qdrant": _qdrant_config(),
            "eventing": {"enabled": _env_bool("EVENTING_ENABLED", True)},
        }

    if mode == MemoryMode.DEVELOPMENT:
        use_testing = _env_bool("REDIS_TESTING", True)
        redis_cfg: Dict[str, Any]
        if use_testing:
            redis_cfg = {"testing": True}
        else:
            redis_cfg = _redis_config()
        config = {
            "redis": redis_cfg,
            "vector": {"backend": "qdrant"},
            "qdrant": _qdrant_config(),
        }
        postgres_url = os.getenv("POSTGRES_URL")
        if postgres_url:
            config["postgres"] = {"url": postgres_url}
        return config

    # TEST mode and other callers rely on factory defaults
    return {}


# Set up a basic tracer provider with console exporter
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

app = FastAPI(title="SomaFractalMemory API")
# Instrument the FastAPI app for tracing
FastAPIInstrumentor().instrument_app(app)


# Generate a static OpenAPI JSON file on startup so docs can reference it.
@app.on_event("startup")
def _write_openapi() -> None:
    import json
    import pathlib

    spec = app.openapi()
    root = pathlib.Path(__file__).resolve().parents[1]
    (root / "openapi.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print("✅ openapi.json generated at", root / "openapi.json")
    # Inform that metrics endpoint is ready
    print("🚀 Metrics endpoint available at /metrics")


_mode_env = os.getenv("MEMORY_MODE", MemoryMode.EVENTED_ENTERPRISE.value).strip().lower()
try:
    memory_mode = MemoryMode(_mode_env)
except ValueError:
    print(f"⚠️ Unsupported MEMORY_MODE '{_mode_env}', defaulting to evented_enterprise")
    memory_mode = MemoryMode.EVENTED_ENTERPRISE

memory_namespace = os.getenv("SOMA_MEMORY_NAMESPACE", "api_ns")
mem = create_memory_system(memory_mode, memory_namespace, config=_build_config(memory_mode))

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
    max_reqs = int(os.getenv("SOMA_RATE_LIMIT_MAX", "1000"))
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


class RememberRequest(BaseModel):
    payload: Dict[str, Any]
    coord: Optional[str] = None
    type: Optional[str] = "episodic"


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
        @wraps(func)
        async def wrapper(*args, **kwargs):
            API_REQUESTS.labels(endpoint=endpoint_name, method=method).inc()
            with API_LATENCY.labels(endpoint=endpoint_name, method=method).time():
                return await func(*args, **kwargs)

        wrapper.__signature__ = inspect.signature(func)
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
    "/remember",
    response_model=OkResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/remember"))],
)
@instrument(endpoint_name="remember", method="POST")
async def remember(req: RememberRequest) -> OkResponse:
    mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    coordinate = parse_coord(req.coord) if req.coord else None
    mem.remember(req.payload, coordinate=coordinate, memory_type=mtype)
    return OkResponse(ok=True)


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
    """Liveness probe – checks basic health of all stores."""
    return HealthResponse(
        kv_store=mem.kv_store.health_check(),
        vector_store=mem.vector_store.health_check(),
        graph_store=mem.graph_store.health_check(),
    )


@app.get("/readyz", response_model=HealthResponse)
def readyz():
    """Readiness probe – same checks for now; can be extended with more strict criteria later."""
    return HealthResponse(
        kv_store=mem.kv_store.health_check(),
        vector_store=mem.vector_store.health_check(),
        graph_store=mem.graph_store.health_check(),
    )
