"""Health and system routes - 100% Django + Django Ninja + Django ORM.

All database access through Django ORM models.
All strings use centralized messages for i18n.
"""

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Router
from ninja.errors import HttpError

from common.utils.logger import get_logger

from ..messages import ErrorCode, SuccessCode, get_message
from ..schemas import HealthResponse, StatsResponse

logger = get_logger(__name__)
router = Router(tags=["system"])


def _get_service():
    """Get the memory service instance."""
    from somafractalmemory.api.core import get_mem

    return get_mem()


def _check_auth(request: HttpRequest) -> None:
    """Check API token authentication."""
    from somafractalmemory.api.core import API_TOKEN

    if not API_TOKEN:
        return

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HttpError(401, get_message(ErrorCode.MISSING_AUTH_HEADER))

    provided = auth_header.split(" ", 1)[1]
    if provided != API_TOKEN:
        raise HttpError(401, get_message(ErrorCode.INVALID_API_TOKEN))


@router.get("/health/basic", response=HealthResponse)
def health_basic(request: HttpRequest) -> HealthResponse:
    """Basic health check endpoint using Django ORM."""
    service = _get_service()
    checks = service.health_check()
    return HealthResponse(**checks)


@router.get("/healthz", response=HealthResponse)
def healthz(request: HttpRequest) -> HealthResponse:
    """Liveness probe using Django ORM."""
    service = _get_service()
    checks = service.health_check()
    if not all(checks.values()):
        raise HttpError(503, get_message(ErrorCode.BACKEND_UNHEALTHY))
    return HealthResponse(**checks)


@router.get("/readyz", response=HealthResponse)
def readyz(request: HttpRequest) -> HealthResponse:
    """Readiness probe using Django ORM."""
    service = _get_service()
    checks = service.health_check()
    return HealthResponse(**checks)


@router.get("/health")
def health_detailed(request: HttpRequest) -> dict:
    """Comprehensive health check with server details and per-tenant stats.

    Returns:
        - Overall status (healthy/degraded/unhealthy)
        - Version and uptime
        - Backend service status with latencies
        - Database statistics
        - Per-tenant memory and graph counts
        - System information
    """
    import os
    import platform
    import time
    from datetime import datetime, timezone

    from django.db import connection

    from somafractalmemory.models import GraphLink, Memory, MemoryNamespace

    start_time = time.time()

    # Track service health
    services = []

    # Check PostgreSQL
    try:
        pg_start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        pg_latency = (time.time() - pg_start) * 1000
        services.append(
            {
                "name": "postgresql",
                "healthy": True,
                "latency_ms": round(pg_latency, 2),
                "details": {"database": connection.settings_dict.get("NAME")},
            }
        )
    except Exception as e:
        services.append(
            {"name": "postgresql", "healthy": False, "latency_ms": 0, "details": {"error": str(e)}}
        )

    # Check Redis
    try:
        import redis

        redis_start = time.time()
        redis_host = os.environ.get("SOMA_REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("SOMA_REDIS_PORT", "6379"))
        redis_password = os.environ.get("SOMA_REDIS_PASSWORD", None)
        r = redis.Redis(host=redis_host, port=redis_port, password=redis_password, socket_timeout=2)
        r.ping()
        redis_latency = (time.time() - redis_start) * 1000
        services.append(
            {
                "name": "redis",
                "healthy": True,
                "latency_ms": round(redis_latency, 2),
                "details": {"host": redis_host, "port": redis_port},
            }
        )
    except Exception as e:
        services.append(
            {"name": "redis", "healthy": False, "latency_ms": 0, "details": {"error": str(e)}}
        )

    # Check Milvus
    try:
        from pymilvus import connections

        milvus_start = time.time()
        milvus_host = os.environ.get("SOMA_MILVUS_HOST", "localhost")
        milvus_port = os.environ.get("SOMA_MILVUS_PORT", "19530")
        connections.connect(alias="health_check", host=milvus_host, port=milvus_port, timeout=2)
        connections.disconnect(alias="health_check")
        milvus_latency = (time.time() - milvus_start) * 1000
        services.append(
            {
                "name": "milvus",
                "healthy": True,
                "latency_ms": round(milvus_latency, 2),
                "details": {"host": milvus_host, "port": milvus_port},
            }
        )
    except Exception as e:
        services.append(
            {"name": "milvus", "healthy": False, "latency_ms": 0, "details": {"error": str(e)}}
        )

    # Database statistics
    try:
        total_memories = Memory.objects.count()
        episodic_count = Memory.objects.filter(memory_type="episodic").count()
        semantic_count = Memory.objects.filter(memory_type="semantic").count()
        total_links = GraphLink.objects.count()
        total_namespaces = MemoryNamespace.objects.count()

        database = {
            "total_memories": total_memories,
            "episodic_memories": episodic_count,
            "semantic_memories": semantic_count,
            "total_graph_links": total_links,
            "total_namespaces": total_namespaces,
        }
    except Exception as e:
        database = {"error": str(e)}

    # Per-tenant stats
    tenants = []
    try:
        tenant_list = Memory.objects.values_list("tenant", flat=True).distinct()
        for tenant in tenant_list:
            tenant_memories = Memory.objects.filter(tenant=tenant)
            tenant_links = GraphLink.objects.filter(tenant=tenant).count()
            tenants.append(
                {
                    "tenant": tenant,
                    "total_memories": tenant_memories.count(),
                    "episodic": tenant_memories.filter(memory_type="episodic").count(),
                    "semantic": tenant_memories.filter(memory_type="semantic").count(),
                    "graph_links": tenant_links,
                }
            )
    except Exception as e:
        tenants.append({"error": str(e)})

    # System info
    system = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": platform.node(),
        "process_id": os.getpid(),
        "django_settings": os.environ.get("DJANGO_SETTINGS_MODULE", "unknown"),
    }

    # Determine overall status
    healthy_count = sum(1 for s in services if s["healthy"])
    if healthy_count == len(services):
        status = "healthy"
    elif healthy_count > 0:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "healthy": status == "healthy",
        "status": status,
        "version": "0.2.0",
        "uptime_seconds": round(time.time() - start_time, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
        "database": database,
        "tenants": tenants,
        "system": system,
    }


@router.get("/stats", response=StatsResponse)
def stats(request: HttpRequest) -> StatsResponse:
    """Return system statistics using Django ORM."""
    service = _get_service()
    try:
        raw = service.stats()
        return StatsResponse(**raw)
    except Exception as exc:
        logger.warning("stats endpoint failed", error=str(exc), exc_info=True)
        raise HttpError(503, get_message(ErrorCode.BACKEND_UNAVAILABLE, service="stats")) from exc


@router.get("/test-stats", response=StatsResponse)
def test_stats(request: HttpRequest) -> StatsResponse:
    """Return stats for the test-memory namespace only."""
    _check_auth(request)

    from somafractalmemory.services import get_memory_service

    test_ns = getattr(settings, "SOMA_TEST_MEMORY_NAMESPACE", "test_ns")
    test_service = get_memory_service(namespace=test_ns)

    try:
        raw = test_service.stats()
        return StatsResponse(**raw)
    except Exception as exc:
        logger.warning("test-stats endpoint failed", error=str(exc), exc_info=True)
        raise HttpError(
            503, get_message(ErrorCode.BACKEND_UNAVAILABLE, service="test-stats")
        ) from exc


@router.get("/metrics", include_in_schema=False)
def metrics(request: HttpRequest) -> HttpResponse:
    """Expose Prometheus metrics."""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@router.get("/", include_in_schema=False)
def root(request: HttpRequest) -> dict:
    """Root endpoint."""
    return {
        "message": get_message(SuccessCode.API_RUNNING),
        "metrics": "/metrics",
    }


@router.get("/ping")
def ping(request: HttpRequest) -> dict:
    """Simple ping endpoint."""
    return {"ping": "pong"}
