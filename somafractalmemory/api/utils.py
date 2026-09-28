"""Shared router utilities for SomaFractalMemory API.

Centralizes helper functions used across memory, search, and graph routers.
Eliminates code duplication (MOD-01 from audit).
"""

import math

from django.conf import settings
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


def get_tenant_from_request(request: HttpRequest, explicit_tenant: str | None = None) -> str:
    """Extract tenant identifier from the authenticated request.

    Priority:
        1. Auth-bound tenant (real token bindings; security boundary)
        2. Explicit ``tenant_id`` from the request body/query (seam contract)
        3. X-Soma-Tenant header
        4. Auth context tenant (standalone mode label)

    Fail-closed (R-05 / F-06, T-5): when no tenant can be resolved the request
    is rejected with HTTP 400. There is no silent ``"default"`` fallback — that
    mixed callers into one shared tenant by omission.

    In standalone mode the bearer token does not bind a data tenant — every
    caller shares one token — so the caller selects the data tenant via
    ``tenant_id`` or the ``X-Soma-Tenant`` header. This keeps every
    store/search/delete scoped to the caller's tenant.

    Args:
        request: The HTTP request
        explicit_tenant: Optional tenant from the request body or query string

    Returns:
        Tenant identifier string

    Raises:
        HttpError 400: If no tenant can be resolved from any source
    """
    auth = getattr(request, "auth", {}) or {}
    auth_tenant = auth.get("tenant")

    # A real auth binding wins over caller-supplied tenant labels.
    if auth_tenant and auth.get("auth_type") != "standalone_token":
        return auth_tenant

    if explicit_tenant and explicit_tenant.strip():
        return explicit_tenant.strip()

    header_tenant = request.headers.get("X-Soma-Tenant")
    if header_tenant and header_tenant.strip():
        return header_tenant.strip()

    if auth_tenant and str(auth_tenant).strip():
        return str(auth_tenant).strip()

    raise HttpError(400, get_message(ErrorCode.MISSING_TENANT))


def ensure_embedding_dim(embedding: list[float] | None) -> None:
    """Ensure a precomputed embedding matches the configured vector dimension.

    Args:
        embedding: Precomputed vector, or None to use the hash fallback

    Raises:
        HttpError 400: If the vector has the wrong dimension or non-finite values
    """
    if embedding is None:
        return

    if not all(isinstance(v, int | float) and math.isfinite(v) for v in embedding):
        raise HttpError(400, get_message(ErrorCode.INVALID_REQUEST))

    # settings/infra.py always defines SOMA_VECTOR_DIM (default 768, shared with
    # the agent's MEM_EMBED_DIM). Read it directly: a missing setting must fail
    # hard here rather than fall back to a guessed dimension and let a mismatch
    # degrade silently into text search.
    expected = int(settings.SOMA_VECTOR_DIM)
    if len(embedding) != expected:
        raise HttpError(
            400,
            get_message(
                ErrorCode.EMBEDDING_DIMENSION_MISMATCH,
                got=len(embedding),
                expected=expected,
            ),
        )


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
