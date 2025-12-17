# somafractalmemory/api/dependencies.py
"""FastAPI dependencies for SomaFractalMemory API."""

from fastapi import HTTPException, Request

from common.config.settings import load_settings
from common.utils.logger import get_logger
from somafractalmemory.core import MemoryType

_settings = load_settings()
logger = get_logger(__name__)
_RATE_LIMITER = None


def set_rate_limiter(limiter) -> None:
    global _RATE_LIMITER
    _RATE_LIMITER = limiter


def get_rate_limiter():
    return _RATE_LIMITER


def safe_parse_coord(coord: str) -> tuple[float, ...]:
    try:
        parts = [p.strip() for p in coord.split(",") if p.strip()]
        if not parts:
            raise ValueError("Empty coordinate")
        return tuple(float(p) for p in parts)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid coord: {coord}") from exc


def resolve_memory_type(value: str | None) -> MemoryType:
    if value is None:
        return MemoryType.EPISODIC
    try:
        return MemoryType(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unsupported memory_type") from exc


def auth_dep(request: Request):
    expected = getattr(_settings, "api_token", None)
    if not expected:
        logger.warning("API token not configured")
        return None
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    provided = auth_header.split(" ", 1)[1]
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return None


def rate_limit_dep(path: str):
    def _enforce(request: Request):
        limiter = get_rate_limiter()
        if limiter is None:
            return
        key = f"global:{path}"
        if not limiter.allow(key):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return _enforce


def get_tenant_from_request(request: Request) -> str:
    tenant = request.headers.get("X-Soma-Tenant")
    if tenant:
        return tenant.strip()
    namespace = request.headers.get("X-Soma-Namespace", "")
    if ":" in namespace:
        tenant = namespace.split(":")[-1].strip()
        if tenant:
            return tenant
    return "default"


def get_tenant_scoped_namespace(request: Request, base_namespace: str | None = None) -> str:
    tenant = get_tenant_from_request(request)
    from somafractalmemory.http_api import mem

    ns = base_namespace or getattr(mem, "namespace", "default")
    if ns.startswith(f"{tenant}:"):
        return ns
    return f"{tenant}:{ns}"
