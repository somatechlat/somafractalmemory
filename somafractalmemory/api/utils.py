"""Shared router utilities for SomaFractalMemory API.

Centralizes helper functions used across memory, search, and graph routers.
Eliminates code duplication (MOD-01 from audit).
"""

from django.http import HttpRequest
from ninja.errors import HttpError

from somafractalmemory.admin.common.messages import ErrorCode, get_message

from .auth import can_access_namespace, has_permission


def safe_parse_coord(coord: str) -> tuple[float, ...]:
    """Parse a coordinate string into a tuple of floats.

    Args:
        coord: Comma-separated coordinate string (e.g. "1.0,2.0,3.0")

    Returns:
        Tuple of float values

    Raises:
        HttpError 400: If coordinate is empty or contains non-numeric values
    """
    try:
        parts = [p.strip() for p in coord.split(",") if p.strip()]
        if not parts:
            raise HttpError(400, get_message(ErrorCode.EMPTY_COORDINATE))
        return tuple(float(p) for p in parts)
    except ValueError as exc:
        raise HttpError(400, get_message(ErrorCode.INVALID_COORDINATE, coord=coord)) from exc


def get_tenant_from_request(request: HttpRequest) -> str:
    """Extract tenant identifier from the authenticated request.

    Priority:
        1. Auth context tenant (from token validation)
        2. X-Soma-Tenant header
        3. Default: "default"

    Args:
        request: The HTTP request

    Returns:
        Tenant identifier string
    """
    auth = getattr(request, "auth", {}) or {}
    if auth.get("tenant"):
        return auth["tenant"]
    tenant = request.headers.get("X-Soma-Tenant")
    if tenant:
        return tenant.strip()
    return "default"


def ensure_permission(request: HttpRequest, permission: str) -> None:
    """Ensure the caller has the required permission.

    Args:
        request: The HTTP request with auth context
        permission: Required permission (read, write, delete)

    Raises:
        HttpError 403: If permission is denied
    """
    if not has_permission(request, permission):
        raise HttpError(403, get_message(ErrorCode.PERMISSION_DENIED))


def ensure_namespace_access(request: HttpRequest, namespace: str) -> None:
    """Ensure the caller can access the target namespace.

    Args:
        request: The HTTP request with auth context
        namespace: The namespace to check access for

    Raises:
        HttpError 403: If namespace access is denied
    """
    if not can_access_namespace(request, namespace):
        raise HttpError(403, get_message(ErrorCode.PERMISSION_DENIED))
