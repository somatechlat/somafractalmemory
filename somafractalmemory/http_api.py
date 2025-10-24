"""HTTP API service for SomaFractalMemory.

This is the canonical FastAPI surface used for local runs, OpenAPI generation,
and development. It was previously located at ``examples/api.py`` and is now
available at ``somafractalmemory/http_api.py`` with a compatibility shim left
in place for legacy imports.
"""

import os
import threading
import time
from typing import Any, Literal
from urllib.parse import urlparse

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.utils.logger import configure_logging, get_logger
from common.utils.opa_client import OPAClient
from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system

print("Loading somafractalmemory.http_api")

logger = get_logger(__name__)
logger.info("Loading somafractalmemory.http_api")


class HealthResponse(BaseModel):
    kv_store: bool
    vector_store: bool
    graph_store: bool


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


def get_opa_client() -> OPAClient:
    # Load settings and get OPA endpoint
    settings = None
    try:
        if load_settings:
            settings = load_settings()
    except Exception:
        settings = None
    opa_host = None
    policy_path = os.getenv("OPA_POLICY_PATH", "soma/authz/allow")
    if settings and getattr(settings, "infra", None):
        opa_host = getattr(settings.infra, "opa", None)
    opa_url = os.getenv("OPA_URL") or (f"http://{opa_host}:8181" if opa_host else "http://opa:8181")
    return OPAClient(opa_url=opa_url, policy_path=policy_path)


OPA = get_opa_client()


def opa_enforce(request: Request, action: str, extra: dict = None):
    # Compose input for OPA
    user = request.headers.get("Authorization", "").replace("Bearer ", "")
    input_data = {
        "user": user,
        "method": request.method,
        "path": request.url.path,
        "action": action,
    }
    if extra:
        input_data.update(extra)
    allowed = OPA.check(input_data)
    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied by policy")


def parse_coord(text: str) -> tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


def safe_parse_coord(text: str) -> tuple[float, ...]:
    """Parse coordinate string and raise HTTP 400 on invalid input.

    Returns a tuple of floats for valid input. This wrapper ensures we return
    a client-friendly HTTP 400 when the payload contains malformed coords
    instead of bubbling ValueError and producing a 500.
    """
    try:
        return parse_coord(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid coord: {text}") from exc


def _resolve_memory_type(value: str | None) -> MemoryType:
    if value is None:
        return MemoryType.EPISODIC
    try:
        return MemoryType(value)
    except ValueError as exc:  # pragma: no cover - defensive validation
        raise HTTPException(status_code=400, detail="Unsupported memory_type") from exc


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
logger = configure_logging("somafractalmemory-api", level=os.getenv("LOG_LEVEL", "INFO")).bind(
    component="http_api"
)

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
            "Unsupported memory mode requested; defaulting to evented_enterprise",
            requested_mode=mode_env,
        )
    return MemoryMode.EVENTED_ENTERPRISE


mem = None
_RATE_LIMITER = None
_RATE_LIMIT_MAX = int(os.getenv("SOMA_RATE_LIMIT_MAX", "60"))
_RATE_WINDOW = float(os.getenv("SOMA_RATE_LIMIT_WINDOW_SECONDS", "60"))


def _redact_dsn(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlparse(url)
        # Drop username/password from netloc
        netloc_parts = p.netloc.split("@")
        redacted_netloc = netloc_parts[-1]
        sanitized = p._replace(netloc=redacted_netloc)
        return sanitized.geturl()
    except Exception:
        return "***"


def _postgres_config(settings: Any | None = None) -> dict[str, Any]:
    """Resolve Postgres configuration with centralized settings fallback.

    Preference order:
    1. ``SOMA_POSTGRES_URL`` environment variable
    2. ``postgres_url`` from settings
    3. ``POSTGRES_URL`` environment variable
    4. Build URL from infra settings or use default
    """
    # Try SOMA_POSTGRES_URL first (our preferred environment variable)
    url = os.getenv("SOMA_POSTGRES_URL")
    if url:
        return {"url": url}

    # Then try postgres_url from settings if available
    if settings and hasattr(settings, "postgres_url"):
        return {"url": settings.postgres_url}

    # Then try legacy POSTGRES_URL
    url = os.getenv("POSTGRES_URL")
    if url:
        return {"url": url}

    # Last resort: build from infra settings or use default
    host = getattr(getattr(settings, "infra", None), "postgres", "postgres")
    return {"url": f"postgresql://soma:soma@{host}:5432/somamemory"}


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
    host = getattr(getattr(settings, "infra", None), "qdrant", None) or os.getenv("QDRANT_HOST")
    if host:
        port = int(os.getenv("QDRANT_PORT", "6333"))
        return {"host": host, "port": port}
    return {}


def _log_startup_config(memory_mode, namespace_default, config, redis_cfg):
    q = config.get("qdrant", {})
    q_loc = q.get("url") or f"{q.get('host','')}:{q.get('port','')}"
    logger.info(
        "api startup",
        mode=memory_mode.value,
        namespace=namespace_default,
        postgres=_redact_dsn(config.get("postgres", {}).get("url")),
        redis_host=redis_cfg.get("host"),
        qdrant=q_loc,
        eventing_enabled=config.get("eventing", {}).get("enabled", True),
    )


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
                logger.warning(
                    "Rate limiter Redis error; falling back to in-memory",
                    error=str(exc),
                )
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
        logger.warning(
            "Unable to initialise Redis rate limiter; using in-memory fallback",
            error=str(exc),
        )
        return fallback


try:
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

    config: dict[str, Any] = {
        "postgres": _postgres_config(settings),
        "vector": {"backend": "qdrant"},
        "qdrant": _qdrant_config(settings),
    }

    redis_cfg = _redis_config(settings)
    if redis_cfg:
        config["redis"] = redis_cfg

    mem = create_memory_system(memory_mode, namespace_default, config=config)
    _log_startup_config(memory_mode, namespace_default, config, redis_cfg)
    _RATE_LIMITER = _build_rate_limiter(redis_cfg)
except Exception as e:
    logger.error(f"FATAL: Error during initialization: {e}", exc_info=True)
    raise


# Authentication dependency
def auth_dep(request: Request):
    """FastAPI dependency that enforces either JWT authentication (when
    enabled via settings) or the static SOMA_API_TOKEN fallback.

    On success, when JWT is used, the decoded claims are attached to
    ``request.state.jwt_claims`` and the claims dict is returned. When the
    static token is used or no claims are required, None is returned.
    """
    # Load settings safely (settings are optional in some environments)
    settings_local = None
    try:
        if load_settings:
            settings_local = load_settings()
    except Exception:
        settings_local = None

    jwt_enabled = getattr(settings_local, "jwt_enabled", False) if settings_local else False
    jwt_issuer = getattr(settings_local, "jwt_issuer", "") if settings_local else ""
    jwt_audience = getattr(settings_local, "jwt_audience", "") if settings_local else ""
    jwt_secret = getattr(settings_local, "jwt_secret", "") if settings_local else ""
    jwt_public_key = getattr(settings_local, "jwt_public_key", "") if settings_local else ""

    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]

    if jwt_enabled:
        # Validate JWT
        try:
            if jwt_public_key:
                key = jwt_public_key
                alg = "RS256"
            elif jwt_secret:
                key = jwt_secret
                alg = "HS256"
            else:
                raise HTTPException(status_code=500, detail="JWT key not configured")
            payload = jwt.decode(
                token,
                key,
                algorithms=[alg],
                issuer=jwt_issuer if jwt_issuer else None,
                audience=jwt_audience if jwt_audience else None,
                options={"require": ["exp", "iat"]},
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="JWT expired")
        except jwt.InvalidIssuerError:
            raise HTTPException(status_code=403, detail="JWT issuer invalid")
        except jwt.InvalidAudienceError:
            raise HTTPException(status_code=403, detail="JWT audience invalid")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=403, detail=f"JWT invalid: {str(e)}")
        # Attach claims for downstream use
        request.state.jwt_claims = payload
        return payload
    else:
        # Static token fallback
        if API_TOKEN:
            if token != API_TOKEN:
                raise HTTPException(status_code=403, detail="Invalid token")
        return None


def rate_limit_dep(path: str):
    def _enforce(request: Request):
        key = f"global:{path}"
        if not _RATE_LIMITER.allow(key):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return _enforce


class MemoryStoreRequest(BaseModel):
    coord: str
    payload: dict[str, Any]
    memory_type: Literal["episodic", "semantic"] = MemoryType.EPISODIC.value


class MemoryStoreResponse(BaseModel):
    coord: str
    memory_type: str
    ok: bool = True


class MemorySearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: dict[str, Any] | None = None


class MemorySearchResponse(BaseModel):
    memories: list[dict[str, Any]]


class MemoryGetResponse(BaseModel):
    memory: dict[str, Any]


class MemoryDeleteResponse(BaseModel):
    coord: str
    deleted: bool


class StatsResponse(BaseModel):
    total_memories: int
    episodic: int
    semantic: int
    vector_count: int | None = None
    namespaces: dict[str, dict[str, int]] | None = None
    vector_collections: dict[str, int] | None = None


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
API_RESPONSES = Counter(
    "api_responses_total",
    "Total number of API responses by status code",
    ["endpoint", "method", "status"],
)


# Lightweight global middleware for metrics to avoid signature issues from wrappers
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    API_REQUESTS.labels(endpoint=path, method=method).inc()
    import time as _t

    start = _t.perf_counter()
    status_code = "500"
    response: Response | JSONResponse | None = None
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
                    response = JSONResponse(
                        status_code=413, content={"detail": "Request entity too large"}
                    )
                else:
                    response = await call_next(request)
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except HTTPException as exc:  # pragma: no cover - FastAPI specific control flow
        status_code = str(exc.status_code)
        raise
    except Exception:
        status_code = "500"
        raise
    finally:
        dur = max(_t.perf_counter() - start, 0.0)
        # Observe duration
        API_LATENCY.labels(endpoint=path, method=method).observe(dur)
        API_RESPONSES.labels(endpoint=path, method=method, status=status_code).inc()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        "Request processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time=process_time,
    )
    return response


@app.post(
    "/memories",
    response_model=MemoryStoreResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.store"))],
)
async def store_memory(req: MemoryStoreRequest, request: Request = None) -> MemoryStoreResponse:
    if request:
        opa_enforce(
            request,
            action="store_memory",
            extra={"coord": req.coord, "memory_type": req.memory_type},
        )
    memory_type = _resolve_memory_type(req.memory_type)
    coord = safe_parse_coord(req.coord)
    mem.store_memory(coord, req.payload, memory_type=memory_type)
    return MemoryStoreResponse(coord=req.coord, memory_type=memory_type.value)


@app.get(
    "/memories/{coord}",
    response_model=MemoryGetResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.fetch"))],
)
def fetch_memory(coord: str, request: Request = None) -> MemoryGetResponse:
    if request:
        opa_enforce(request, action="fetch_memory", extra={"coord": coord})
    try:
        parsed = safe_parse_coord(coord)
    except HTTPException:
        raise
    record = mem.retrieve(parsed)
    if not record:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryGetResponse(memory=record)


@app.delete(
    "/memories/{coord}",
    response_model=MemoryDeleteResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.delete"))],
)
def delete_memory(coord: str, request: Request = None) -> MemoryDeleteResponse:
    if request:
        opa_enforce(request, action="delete_memory", extra={"coord": coord})
    try:
        parsed = safe_parse_coord(coord)
    except HTTPException:
        raise
    deleted = mem.delete(parsed)
    return MemoryDeleteResponse(coord=coord, deleted=bool(deleted))


@app.post(
    "/memories/search",
    response_model=MemorySearchResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.search"))],
)
def search_memories(req: MemorySearchRequest, request: Request = None) -> MemorySearchResponse:
    if request:
        opa_enforce(request, action="search_memories", extra={"query": req.query})
    if req.filters:
        results = mem.find_hybrid_by_type(req.query, top_k=req.top_k, filters=req.filters)
    else:
        results = mem.recall(req.query, top_k=req.top_k)
    return MemorySearchResponse(memories=results)


@app.get(
    "/memories/search",
    response_model=MemorySearchResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/memories.search"))],
)
def search_memories_get(
    query: str,
    top_k: int = 5,
    filters: str | None = None,
    request: Request = None,
) -> MemorySearchResponse:
    if request:
        opa_enforce(request, action="search_memories_get", extra={"query": query})
    parsed_filters: dict[str, Any] | None = None
    if filters:
        try:
            import json as _json

            parsed_candidate = _json.loads(filters)
            if isinstance(parsed_candidate, dict):
                parsed_filters = parsed_candidate
        except Exception:
            parsed_filters = None
    if parsed_filters:
        results = mem.find_hybrid_by_type(query, top_k=top_k, filters=parsed_filters)
    else:
        results = mem.recall(query, top_k=top_k)
    return MemorySearchResponse(memories=results)


@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["system"],
    # Stats is read-only operational info and is intentionally public so
    # infrastructure/monitoring systems can scrape it without needing the
    # bearer token. We keep rate limiting enabled to avoid abuse.
    dependencies=[Depends(rate_limit_dep("/stats"))],
)
def stats() -> StatsResponse:
    try:
        return StatsResponse(**mem.memory_stats())
    except Exception as exc:  # pragma: no cover - depends on backend state
        logger.warning("stats endpoint failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=503, detail="Backend stats unavailable") from exc


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(**mem.health_check())


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


@app.get("/ping")
def ping():
    return {"ping": "pong"}


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


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"An unexpected error occurred: {exc}", exc_info=True)
    return await fastapi_http_exception_handler(
        request, HTTPException(status_code=500, detail="Internal Server Error")
    )


# Health and readiness endpoints
@app.get("/healthz", response_model=HealthResponse)
def healthz():
    """Liveness probe – checks basic health of storage/vector/graph components."""
    checks = mem.health_check()
    return HealthResponse(
        kv_store=checks.get("kv_store", False),
        vector_store=checks.get("vector_store", False),
        graph_store=checks.get("graph_store", False),
    )


@app.get("/readyz", response_model=HealthResponse)
def readyz():
    """Readiness probe – same checks for now; can be extended with more strict criteria later."""
    checks = mem.health_check()
    return HealthResponse(
        kv_store=checks.get("kv_store", False),
        vector_store=checks.get("vector_store", False),
        graph_store=checks.get("graph_store", False),
    )
