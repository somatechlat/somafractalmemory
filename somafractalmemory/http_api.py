"""HTTP API service for SomaFractalMemory.

This is the canonical FastAPI surface used for local runs, OpenAPI generation,
and development. Route handlers are extracted to somafractalmemory/api/routes/.

VIBE Compliance: This file is under 500 lines after decomposition.
"""

import os
import threading
import time
import warnings
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from prometheus_client import CollectorRegistry, Counter, Histogram
from starlette.exceptions import HTTPException as StarletteHTTPException

try:
    import redis
    from redis.exceptions import RedisError
except ImportError:
    # type: ignore[assignment,misc] - redis is optional; fallback for environments without it
    redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[misc,assignment]

from common.config.settings import load_settings
from common.utils.async_metrics import submit as _submit_metric
from common.utils.logger import configure_logging, get_logger
from common.utils.trace import configure_tracer
from somafractalmemory.factory import MemoryMode, create_memory_system

warnings.filterwarnings("ignore", category=DeprecationWarning)

_settings = load_settings()
_USE_ASYNC_METRICS = _settings.async_metrics_enabled


def _maybe_submit(fn):
    """Submit metric update, with sync fallback."""
    if _USE_ASYNC_METRICS:
        try:
            _submit_metric(fn)
            return
        except Exception:
            pass
    try:
        fn()
    except Exception:
        pass


print("Loading somafractalmemory.http_api")
logger = get_logger(__name__)
logger.info("Loading somafractalmemory.http_api")

# Configure tracing
if configure_tracer:
    try:
        configure_tracer("somafractalmemory-api")
    except Exception:
        pass
else:
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

logger = configure_logging(
    "somafractalmemory-api",
    level=_settings.log_level,
).bind(component="http_api")

# Create FastAPI app
app = FastAPI(title="SomaFractalMemory API")
FastAPIInstrumentor().instrument_app(app)

# CORS configuration
_cors_origins_env = _settings.cors_origins
if _cors_origins_env:
    origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            max_age=600,
        )

_RATE_LIMIT_MAX = int(_settings.rate_limit_max)
_RATE_WINDOW = float(_settings.rate_limit_window)


# ---------------------------------------------------------------------
# Rate Limiter Classes
# ---------------------------------------------------------------------
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
                    "Rate limiter Redis error; falling back to in-memory", error=str(exc)
                )
                self._warned = True
            if self._fallback:
                return self._fallback.allow(key)
            return True


def _build_rate_limiter(cfg: dict[str, Any]) -> object:
    """Construct a rate limiter."""
    if _RATE_LIMIT_MAX <= 0 or _RATE_WINDOW <= 0:
        return _AlwaysAllowRateLimiter()
    fallback = _InMemoryRateLimiter(window=_RATE_WINDOW, max_requests=_RATE_LIMIT_MAX)
    if cfg.get("enabled") is False:
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
    except Exception as exc:
        logger.warning(
            "Unable to initialise Redis rate limiter; using in-memory fallback", error=str(exc)
        )
        return fallback


# ---------------------------------------------------------------------
# Configuration Helpers
# ---------------------------------------------------------------------
def _redact_dsn(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlparse(url)
        netloc_parts = p.netloc.split("@")
        redacted_netloc = netloc_parts[-1]
        sanitized = p._replace(netloc=redacted_netloc)
        return sanitized.geturl()
    except Exception:
        return "***"


def _postgres_config(settings: Any | None = None) -> dict[str, Any]:
    # Use centralized settings - Pydantic handles SOMA_POSTGRES_URL env var
    if settings and hasattr(settings, "postgres_url") and settings.postgres_url:
        return {"url": str(settings.postgres_url)}
    host = getattr(getattr(settings, "infra", None), "postgres", "postgres")
    return {"url": f"postgresql://soma:soma@{host}:5432/somamemory"}


def _redis_config(settings: Any | None = None) -> dict[str, Any]:
    # Use centralized settings - Pydantic handles SOMA_REDIS_* env vars
    cfg: dict[str, Any] = {}
    if settings and getattr(settings, "infra", None):
        cfg["host"] = settings.infra.redis
    if hasattr(_settings, "redis_port"):
        cfg["port"] = _settings.redis_port
    if hasattr(_settings, "redis_db"):
        cfg["db"] = _settings.redis_db
    return cfg


def _log_startup_config(memory_mode, namespace_default, config, redis_cfg):
    logger.info(
        "api startup",
        mode=memory_mode.value,
        namespace=namespace_default,
        postgres=_redact_dsn(config.get("postgres", {}).get("url")),
        redis_host=redis_cfg.get("host"),
    )


def _load_api_token() -> str | None:
    """Load the API token from settings or .env file."""
    token_file = getattr(_settings, "api_token_file", None)
    if token_file and os.path.exists(token_file):
        try:
            with open(token_file, encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    token = getattr(_settings, "api_token", None)
    if token:
        return token

    import pathlib

    possible_paths = [
        pathlib.Path(__file__).resolve().parents[1] / ".env",
        pathlib.Path.cwd() / ".env",
    ]
    for env_path in possible_paths:
        if env_path.is_file():
            try:
                with env_path.open(encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("SOMA_API_TOKEN"):
                            return line.strip().split("=", 1)[1]
            except Exception:
                continue
    return None


# ---------------------------------------------------------------------
# Memory System Initialization
# ---------------------------------------------------------------------
API_TOKEN = _load_api_token()
if not API_TOKEN:
    raise RuntimeError(
        "SOMA_API_TOKEN (or SOMA_API_TOKEN_FILE) must be set before importing somafractalmemory.http_api."
    )

mem = None
_RATE_LIMITER = None

try:
    mode_env = _settings.memory_mode.lower()
    if mode_env != MemoryMode.EVENTED_ENTERPRISE.value:
        logger.warning(
            "Unsupported memory mode; defaulting to evented_enterprise", requested_mode=mode_env
        )
    memory_mode = MemoryMode.EVENTED_ENTERPRISE

    settings = load_settings()
    namespace_default = getattr(settings, "namespace", _settings.memory_namespace)

    config: dict[str, Any] = {
        "postgres": _postgres_config(settings),
    }

    redis_cfg = _redis_config(settings)
    if redis_cfg and redis_cfg.get("host") not in ("redis", None):
        config["redis"] = redis_cfg

    mem = create_memory_system(memory_mode, namespace_default, config=config)
    _log_startup_config(memory_mode, namespace_default, config, redis_cfg)
    _RATE_LIMITER = _build_rate_limiter(redis_cfg)

    # Set rate limiter in dependencies module for routes to use
    from somafractalmemory.api.dependencies import set_rate_limiter

    set_rate_limiter(_RATE_LIMITER)
except Exception as e:
    logger.error(f"FATAL: Error during initialization: {e}", exc_info=True)
    raise


# ---------------------------------------------------------------------
# Prometheus Metrics Initialization
# ---------------------------------------------------------------------
def _init_metrics() -> None:
    if getattr(app.state, "metrics_initialized", False):
        return
    registry = CollectorRegistry()
    app.state.API_REQUESTS = Counter(
        "api_requests_total",
        "Total number of API requests",
        ["endpoint", "method"],
        registry=registry,
    )
    app.state.API_LATENCY = Histogram(
        "api_request_latency_seconds",
        "Latency of API requests in seconds",
        ["endpoint", "method"],
        registry=registry,
    )
    app.state.API_RESPONSES = Counter(
        "api_responses_total",
        "Total number of API responses by status code",
        ["endpoint", "method", "status"],
        registry=registry,
    )
    app.state.DELETE_SUCCESS = Counter(
        "api_delete_success_total",
        "Number of successful memory delete operations",
        ["endpoint"],
        registry=registry,
    )
    app.state.metrics_registry = registry
    app.state.metrics_initialized = True


@app.on_event("startup")
async def _startup_metrics() -> None:
    _init_metrics()


# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    if hasattr(app.state, "API_REQUESTS"):
        _maybe_submit(lambda: app.state.API_REQUESTS.labels(endpoint=path, method=method).inc())
    start = time.perf_counter()
    status_code = "500"
    try:
        max_mb = float(_settings.max_request_body_mb)
        if max_mb > 0:
            cl = request.headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > int(max_mb * 1024 * 1024):
                return JSONResponse(status_code=413, content={"detail": "Request entity too large"})
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except HTTPException as exc:
        status_code = str(exc.status_code)
        raise
    finally:
        dur = max(time.perf_counter() - start, 0.0)
        if hasattr(app.state, "API_LATENCY"):
            _maybe_submit(
                lambda: app.state.API_LATENCY.labels(endpoint=path, method=method).observe(dur)
            )
        if hasattr(app.state, "API_RESPONSES"):
            _maybe_submit(
                lambda: app.state.API_RESPONSES.labels(
                    endpoint=path, method=method, status=status_code
                ).inc()
            )


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


# ---------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------
HTTP_404_REQUESTS = Counter("http_404_requests_total", "Total number of HTTP 404 responses")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        _maybe_submit(lambda: HTTP_404_REQUESTS.inc())
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"An unexpected error occurred: {exc}", exc_info=True)
    return await fastapi_http_exception_handler(
        request, HTTPException(status_code=500, detail="Internal Server Error")
    )


# ---------------------------------------------------------------------
# Register Routers (imported after mem is initialized to avoid circular imports)
# ---------------------------------------------------------------------
from somafractalmemory.api.routes import (  # noqa: E402
    graph_router,
    health_router,
    memory_router,
    search_router,
)

app.include_router(memory_router)
app.include_router(search_router)
app.include_router(health_router)
app.include_router(graph_router)
