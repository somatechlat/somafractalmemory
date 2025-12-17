# somafractalmemory/api/routes/health.py
"""Health and system route handlers for SomaFractalMemory API.

Extracted from http_api.py for VIBE compliance (<500 lines per file).
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..dependencies import auth_dep, rate_limit_dep
from ..schemas import HealthResponse, StatsResponse

logger = structlog.get_logger()
router = APIRouter(tags=["system"])


def get_mem():
    """Get the memory system instance. Imported at runtime to avoid circular imports."""
    from somafractalmemory.http_api import mem

    return mem


def get_settings():
    """Get settings instance."""
    from common.config.settings import load_settings

    return load_settings()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Basic health check endpoint."""
    mem = get_mem()
    return HealthResponse(**mem.health_check())


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """Liveness probe – checks basic health of storage/vector/graph components."""
    mem = get_mem()
    checks = mem.health_check()
    if not (checks.get("kv_store") and checks.get("vector_store") and checks.get("graph_store")):
        raise HTTPException(status_code=503, detail="One or more backend services unhealthy")
    return HealthResponse(
        kv_store=checks.get("kv_store", False),
        vector_store=checks.get("vector_store", False),
        graph_store=checks.get("graph_store", False),
    )


@router.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    """Readiness probe – same checks for now."""
    mem = get_mem()
    checks = mem.health_check()
    return HealthResponse(
        kv_store=checks.get("kv_store", False),
        vector_store=checks.get("vector_store", False),
        graph_store=checks.get("graph_store", False),
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    dependencies=[Depends(rate_limit_dep("/stats"))],
)
def stats() -> StatsResponse:
    """Return system statistics.

    Stats is read-only operational info and is intentionally public so
    infrastructure/monitoring systems can scrape it without needing the
    bearer token.
    """
    mem = get_mem()
    try:
        raw = mem.memory_stats()
        if raw.get("total_memories", 0) == 0 and raw.get("vector_count", 0) > 0:
            raw["total_memories"] = raw["vector_count"]
        return StatsResponse(**raw)
    except Exception as exc:
        logger.warning("stats endpoint failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=503, detail="Backend stats unavailable") from exc


@router.get(
    "/test-stats",
    response_model=StatsResponse,
    dependencies=[Depends(auth_dep), Depends(rate_limit_dep("/test-stats"))],
)
def test_stats() -> StatsResponse:
    """Return stats for the test-memory namespace only."""
    mem = get_mem()
    _settings = get_settings()
    try:
        raw = mem.memory_stats()
        test_ns = getattr(_settings, "test_memory_namespace", "test_ns")
        ns_data = raw.get("namespaces", {}).get(
            test_ns,
            {"total": 0, "episodic": 0, "semantic": 0},
        )
        return StatsResponse(
            total_memories=ns_data.get("total", 0),
            episodic=ns_data.get("episodic", 0),
            semantic=ns_data.get("semantic", 0),
            vector_count=raw.get("vector_count"),
            namespaces={test_ns: ns_data},
            vector_collections=raw.get("vector_collections"),
        )
    except Exception as exc:
        logger.warning("test-stats endpoint failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=503, detail="Backend stats unavailable") from exc


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Expose Prometheus metrics for the FastAPI server."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/", include_in_schema=False)
def root() -> dict:
    """Root endpoint that points users to the metrics URL."""
    return {"message": "SomaFractalMemory API is running", "metrics": "/metrics"}


@router.get("/ping")
def ping():
    """Simple ping endpoint."""
    return {"ping": "pong"}
