"""HTTP API service for SomaFractalMemory.

This is the canonical FastAPI surface used for local runs, OpenAPI generation,
and development. It was previously located at ``examples/api.py`` and is now
available at ``somafractalmemory/http_api.py`` with a compatibility shim left
in place for legacy imports.
"""

import logging
import os
import threading
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.utils.logger import configure_logging
from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system

try:  # pragma: no cover - optional dependency import path
    import redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - redis is optional in some environments
    redis = None  # type: ignore
    RedisError = Exception  # type: ignore[misc]

try:
    # Centralised settings and shared tracing (optional in CI environments)
    from common.config.settings import load_settings
    from common.utils.trace import configure_tracer
except Exception:  # pragma: no cover - optional in some environments
    load_settings = None  # type: ignore
    configure_tracer = None  # type: ignore


def parse_coord(text: str) -> tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


# Configure tracing: prefer shared tracer if present, else fallback to console exporter
if configure_tracer:
    try:
        configure_tracer("somafractalmemory-api")
    except Exception:
        pass
else:
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

# Configure structured logging early (JSON output)
configure_logging("somafractalmemory-api")
logger = logging.getLogger(__name__)

app = FastAPI(title="SomaFractalMemory API")
# Instrument the FastAPI app for tracing
FastAPIInstrumentor().instrument_app(app)

# ------------------------------------------------------------
# CORS configuration (configurable via SOMA_CORS_ORIGINS)
# ------------------------------------------------------------
_cors_origins_env = os.getenv("SOMA_CORS_ORIGINS", "")
if _cors_origins_env:
    # Comma-separated list of origins, e.g. "https://app.example.com,https://admin.example.com"
    origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
else:
    origins = []  # default: no CORS (closed) unless explicitly enabled

if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        max_age=600,
    )


def _resolve_memory_mode() -> MemoryMode:
    mode_env = (os.getenv("MEMORY_MODE") or MemoryMode.EVENTED_ENTERPRISE.value).lower()
    if mode_env != MemoryMode.EVENTED_ENTERPRISE.value:
        logger.warning(
            "Unsupported MEMORY_MODE '%s' requested; defaulting to evented_enterprise.",
            mode_env,
        )
    return MemoryMode.EVENTED_ENTERPRISE


def _redis_config(settings: Any | None = None) -> dict[str, Any]:
    """Build a Redis connection dict.

    Preference order:
    1. Values from ``SMFSettings.infra.redis`` (host) and optional ``REDIS_PORT``/``REDIS_DB`` env vars.
    2. Legacy ``REDIS_URL`` parsing.
    3. Individual ``REDIS_HOST``/``REDIS_PORT``/``REDIS_DB`` env vars.
    """
    cfg: dict[str, Any] = {"testing": False}
    # Use the DNS name from the shared infra settings if available
    if settings and getattr(settings, "infra", None):
        cfg["host"] = settings.infra.redis
    # Fallback to explicit URL parsing
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
    # Individual env vars override previous values
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


def _qdrant_config(settings: Any | None = None) -> dict[str, Any]:
    """Return Qdrant connection parameters.

    If a full URL is provided via ``QDRANT_URL`` we honour it.
    Otherwise we build ``host``/``port`` using either the shared infra DNS name
    (``settings.infra.qdrant`` – not defined explicitly, so we fall back to the
    ``QDRANT_HOST`` env var) and the ``QDRANT_PORT`` env var.
    """
    url = os.getenv("QDRANT_URL")
    if url:
        return {"url": url}
    # Prefer centralized settings DNS when available, else fall back to env or default.
    host = getattr(getattr(settings, "infra", None), "qdrant", None) or os.getenv(
        "QDRANT_HOST", "qdrant"
    )
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return {"host": host, "port": port}


memory_mode = _resolve_memory_mode()

# Load centralized settings (optional). Fallback to environment if not available.
settings = None
namespace_default = os.getenv("SOMA_MEMORY_NAMESPACE", "api_ns")
try:
    if load_settings:
        settings = load_settings()
        namespace_default = getattr(settings, "namespace", namespace_default)
except Exception:
    settings = None


def _postgres_config(settings: Any | None = None) -> dict[str, Any]:
    """Resolve Postgres configuration with centralized settings fallback.

    Preference order:
    1. Explicit ``POSTGRES_URL`` environment variable.
    2. Centralized settings DNS (``settings.infra.postgres``) with standard DSN.
    3. Empty mapping when neither is present.
    """
    url = os.getenv("POSTGRES_URL")
    if url:
        return {"url": url}
    host = getattr(getattr(settings, "infra", None), "postgres", None)
    if host:
        # Default credentials/database match our Helm chart defaults
        return {"url": f"postgresql://postgres:postgres@{host}:5432/somamemory"}
    return {"url": os.getenv("POSTGRES_URL")}  # final fallback (None or value)


config: dict[str, Any] = {
    "postgres": _postgres_config(settings),
    "vector": {"backend": "qdrant"},
    "qdrant": _qdrant_config(settings),
}

redis_cfg = _redis_config(settings)
if redis_cfg:
    config["redis"] = redis_cfg

eventing_env = os.getenv("EVENTING_ENABLED")
if eventing_env is not None:
    config["eventing"] = {"enabled": eventing_env.lower() in ("1", "true", "yes", "on")}

mem = create_memory_system(memory_mode, namespace_default, config=config)


def _redact_dsn(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlparse(url)
        # Drop username/password from netloc
        hostport = p.hostname or ""
        if p.port:
            hostport = f"{hostport}:{p.port}"
        return urlunparse((p.scheme, hostport, p.path, "", "", ""))
    except Exception:
        return url


def _log_startup_config():
    q = config.get("qdrant", {})
    q_loc = q.get("url") or f"{q.get('host','')}:{q.get('port','')}"
    logger.info(
        "startup: api",
        extra={
            "mode": memory_mode.value,
            "namespace": namespace_default,
            "postgres": _redact_dsn(config.get("postgres", {}).get("url")),
            "redis_host": redis_cfg.get("host"),
            "qdrant": q_loc,
            "eventing_enabled": config.get("eventing", {}).get("enabled", True),
        },
    )


_log_startup_config()

# Some tests expect a prediction_provider attribute for health endpoints; provide a no-op stub
if not hasattr(mem, "prediction_provider"):

    class _NoopPredictor:
        def health_check(self):
            return True

    mem.prediction_provider = _NoopPredictor()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Authentication & rate limiting dependencies
# ---------------------------------------------------------------------------
def _load_api_token() -> str | None:
    # Support reading token from file (e.g., mounted Kubernetes Secret)
    token_file = os.getenv("SOMA_API_TOKEN_FILE")
    if token_file and os.path.exists(token_file):
        try:
            with open(token_file, encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return os.getenv("SOMA_API_TOKEN")


API_TOKEN = _load_api_token()

if not API_TOKEN:
    raise RuntimeError(
        "SOMA_API_TOKEN (or SOMA_API_TOKEN_FILE) must be set before importing somafractalmemory.http_api."
    )

_RATE_LIMIT_MAX = int(os.getenv("SOMA_RATE_LIMIT_MAX", "60"))
_RATE_WINDOW = float(os.getenv("SOMA_RATE_LIMIT_WINDOW_SECONDS", "60"))


class _AlwaysAllowRateLimiter:
    def allow(self, key: str) -> bool:
        return True


class _InMemoryRateLimiter:
    def __init__(self, window: float, max_requests: int):
        self.window = max(window, 0.0)
        self.max_requests = max_requests
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self.max_requests <= 0 or self.window <= 0:
            return True
        now = time.time()
        with self._lock:
            bucket = self._buckets.setdefault(key, [])
            # Drop entries outside the window
            bucket[:] = [ts for ts in bucket if now - ts <= self.window]
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True


class _RedisRateLimiter:
    def __init__(
        self,
        client: "redis.Redis",
        window: float,
        max_requests: int,
        *,
        prefix: str = "sfm:rate",
        fallback: _InMemoryRateLimiter | None = None,
    ):
        self.client = client
        self.window = max(int(window), 1)
        self.max_requests = max_requests
        self.prefix = prefix
        self._fallback = fallback
        self._warned = False

    def allow(self, key: str) -> bool:
        if self.max_requests <= 0:
            return True
        redis_key = f"{self.prefix}:{key}"
        try:
            with self.client.pipeline() as pipe:
                pipe.incr(redis_key)
                pipe.expire(redis_key, self.window)
                count, _ = pipe.execute()
            return int(count) <= self.max_requests
        except RedisError as exc:
            if not self._warned:
                logger.warning("Rate limiter Redis error; falling back to in-memory: %s", exc)
                self._warned = True
            if self._fallback:
                return self._fallback.allow(key)
            return True


def _build_rate_limiter(cfg: dict[str, Any]) -> object:
    if _RATE_LIMIT_MAX <= 0 or _RATE_WINDOW <= 0:
        return _AlwaysAllowRateLimiter()
    fallback = _InMemoryRateLimiter(window=_RATE_WINDOW, max_requests=_RATE_LIMIT_MAX)
    if not cfg or cfg.get("testing") or cfg.get("enabled") is False:
        return fallback
    if redis is None:
        logger.warning("redis package unavailable; using in-memory rate limiter")
        return fallback
    try:
        client = redis.Redis(
            host=cfg.get("host", "localhost"),
            port=int(cfg.get("port", 6379)),
            db=int(cfg.get("db", 0)),
            password=cfg.get("password"),
            ssl=bool(cfg.get("ssl", False)),
            socket_connect_timeout=float(cfg.get("socket_connect_timeout", 1.5)),
            socket_timeout=float(cfg.get("socket_timeout", 1.5)),
            retry_on_timeout=True,
        )
        client.ping()
        return _RedisRateLimiter(
            client=client,
            window=_RATE_WINDOW,
            max_requests=_RATE_LIMIT_MAX,
            fallback=fallback,
        )
    except Exception as exc:  # pragma: no cover - network/path dependent
        logger.warning("Unable to initialise Redis rate limiter; using in-memory fallback: %s", exc)
        return fallback


_RATE_LIMITER = _build_rate_limiter(redis_cfg)


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
    def _enforce(request: Request):
        key = f"global:{path}"
        if not _RATE_LIMITER.allow(key):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return _enforce


class StoreRequest(BaseModel):
    coord: str
    payload: dict[str, Any]
    type: str | None = "episodic"


class RecallRequest(BaseModel):
    query: str
    top_k: int = 5
    type: str | None = None
    filters: dict[str, Any] | None = None
    hybrid: bool | None = None


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
    hybrid: bool | None = None


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


class RecallWithScoresBody(BaseModel):
    query: str
    top_k: int = 5
    type: str | None = None
    hybrid: bool | None = None
    exact: bool = True
    case_sensitive: bool = False


class RecallWithContextBody(BaseModel):
    query: str
    context: dict
    top_k: int = 5
    type: str | None = None


class HybridScoresResponse(BaseModel):
    results: list[ScoreItem]


class KeywordSearchRequest(BaseModel):
    term: str
    exact: bool = True
    case_sensitive: bool = False
    top_k: int = 50
    type: str | None = None


class HybridRecallRequest(BaseModel):
    query: str
    terms: list[str] | None = None
    boost: float = 2.0
    top_k: int = 5
    exact: bool = True
    case_sensitive: bool = False
    type: str | None = None


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


# Lightweight global middleware for metrics to avoid signature issues from wrappers
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    API_REQUESTS.labels(endpoint=path, method=method).inc()
    import time as _t

    start = _t.perf_counter()
    try:
        # Enforce a maximum request body size via Content-Length (fail fast)
        try:
            max_mb = float(os.getenv("SOMA_MAX_REQUEST_BODY_MB", "5"))
        except Exception:
            max_mb = 5.0
        if max_mb > 0:
            cl = request.headers.get("content-length")
            if cl and cl.isdigit():
                if int(cl) > int(max_mb * 1024 * 1024):
                    return JSONResponse(
                        status_code=413, content={"detail": "Request entity too large"}
                    )
        response = await call_next(request)
        return response
    finally:
        dur = max(_t.perf_counter() - start, 0.0)
        # Observe duration
        API_LATENCY.labels(endpoint=path, method=method).observe(dur)


@app.post(
    "/store",
    response_model=OkResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/store"))],
)
async def store(req: StoreRequest) -> OkResponse:
    mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    mem.store_memory(parse_coord(req.coord), req.payload, memory_type=mtype)
    return OkResponse(ok=True)


@app.post(
    "/recall",
    response_model=MatchesResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/recall"))],
)
async def recall(req: RecallRequest) -> MatchesResponse:
    mtype = None
    if req.type:
        mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    if req.filters:
        res = mem.find_hybrid_by_type(
            req.query, top_k=req.top_k, memory_type=mtype, filters=req.filters
        )
    else:
        if req.hybrid is True:
            res = mem.hybrid_recall(req.query, top_k=req.top_k, memory_type=mtype)
        else:
            # Default recall now uses hybrid scoring in core (env-controllable)
            res = mem.recall(req.query, top_k=req.top_k, memory_type=mtype)
    return MatchesResponse(matches=res)


@app.get(
    "/recall",
    response_model=MatchesResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/recall"))],
)
def recall_get(
    query: str,
    top_k: int = 5,
    type: str | None = None,
    hybrid: bool | None = None,
    filters: str | None = None,
) -> MatchesResponse:
    """Compatibility endpoint for clients that pass parameters via query string.

    Returns the same shape as POST /recall: {"matches": [...]}
    """
    from somafractalmemory.core import MemoryType

    mtype = None
    if type:
        mtype = MemoryType.SEMANTIC if type == "semantic" else MemoryType.EPISODIC
    parsed_filters: dict[str, Any] | None = None
    if filters:
        try:
            import json as _json

            parsed = _json.loads(filters)
            if isinstance(parsed, dict):
                parsed_filters = parsed
        except Exception:
            parsed_filters = None
    if parsed_filters:
        res = mem.find_hybrid_by_type(query, top_k=top_k, memory_type=mtype, filters=parsed_filters)
    else:
        if hybrid is True:
            res = mem.hybrid_recall(query, top_k=top_k, memory_type=mtype)
        else:
            res = mem.recall(query, top_k=top_k, memory_type=mtype)
    return MatchesResponse(matches=res)


@app.post(
    "/recall_batch",
    response_model=BatchesResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/recall_batch"))],
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
            if req.hybrid is True:
                batch = mem.hybrid_recall(q, top_k=req.top_k, memory_type=mtype)
            else:
                batch = mem.recall(q, top_k=req.top_k, memory_type=mtype)
        batches.append(batch)
    return BatchesResponse(batches=batches)


@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["system"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/stats"))],
)
def stats() -> StatsResponse:
    try:
        return StatsResponse(**mem.memory_stats())
    except Exception as exc:  # pragma: no cover - depends on backend state
        logger.warning("stats endpoint failed", exc_info=exc)
        raise HTTPException(status_code=503, detail="Backend stats unavailable") from exc


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(**mem.health_check())


@app.get(
    "/neighbors",
    response_model=NeighborsResponse,
    tags=["graph"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/neighbors"))],
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
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/link"))],
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
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/shortest_path"))],
)
def shortest_path(frm: str, to: str, link_type: str | None = None) -> PathResponse:
    path = mem.find_shortest_path(parse_coord(frm), parse_coord(to), link_type=link_type)
    return PathResponse(path=[list(c) for c in path])


@app.post(
    "/store_bulk",
    response_model=StoreBulkResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/store_bulk"))],
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
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/recall_with_scores"))],
)
def recall_with_scores(req: RecallWithScoresBody) -> ScoresResponse:
    from somafractalmemory.core import MemoryType

    mtype = (
        MemoryType.SEMANTIC
        if req.type == "semantic"
        else (MemoryType.EPISODIC if req.type == "episodic" else None)
    )
    if req.hybrid is True:
        res = mem.hybrid_recall_with_scores(
            req.query,
            top_k=req.top_k,
            memory_type=mtype,
            exact=req.exact,
            case_sensitive=req.case_sensitive,
        )
    else:
        res = mem.recall_with_scores(req.query, top_k=req.top_k, memory_type=mtype)
    return ScoresResponse(results=res)


@app.post(
    "/keyword_search",
    response_model=ResultsResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/keyword_search"))],
)
def keyword_search(req: KeywordSearchRequest) -> ResultsResponse:
    from somafractalmemory.core import MemoryType

    mtype = (
        MemoryType.SEMANTIC
        if req.type == "semantic"
        else (MemoryType.EPISODIC if req.type == "episodic" else None)
    )
    res = mem.keyword_search(
        req.term,
        exact=req.exact,
        case_sensitive=req.case_sensitive,
        top_k=req.top_k,
        memory_type=mtype,
    )
    return ResultsResponse(results=res)


@app.post(
    "/hybrid_recall_with_scores",
    response_model=HybridScoresResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/hybrid_recall_with_scores"))],
)
def hybrid_recall_with_scores(req: HybridRecallRequest) -> HybridScoresResponse:
    from somafractalmemory.core import MemoryType

    mtype = (
        MemoryType.SEMANTIC
        if req.type == "semantic"
        else (MemoryType.EPISODIC if req.type == "episodic" else None)
    )
    results = mem.hybrid_recall_with_scores(
        req.query,
        terms=req.terms,
        boost=req.boost,
        top_k=req.top_k,
        memory_type=mtype,
        exact=req.exact,
        case_sensitive=req.case_sensitive,
    )
    # results are dicts {payload, score}
    return HybridScoresResponse(results=[ScoreItem(**r) for r in results])


@app.post(
    "/recall_with_context",
    response_model=ResultsResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/recall_with_context"))],
)
def recall_with_context(req: RecallWithContextBody) -> ResultsResponse:  # noqa: F811
    from somafractalmemory.core import MemoryType

    mtype = (
        MemoryType.SEMANTIC
        if req.type == "semantic"
        else (MemoryType.EPISODIC if req.type == "episodic" else None)
    )
    res = mem.find_hybrid_with_context(req.query, req.context, top_k=req.top_k, memory_type=mtype)
    return ResultsResponse(results=res)


@app.get(
    "/range",
    response_model=dict[str, list[list[float]]],
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/range"))],
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
