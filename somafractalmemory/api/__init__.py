# somafractalmemory/api/__init__.py
"""API module for SomaFractalMemory HTTP endpoints.

This module contains extracted components from http_api.py for VIBE compliance
(<500 lines per file).
"""

from .dependencies import (
    auth_dep,
    get_rate_limiter,
    get_tenant_from_request,
    get_tenant_scoped_namespace,
    rate_limit_dep,
    resolve_memory_type,
    safe_parse_coord,
    set_rate_limiter,
)
from .schemas import (
    GraphLinkRequest,
    GraphLinkResponse,
    GraphNeighborsRequest,
    GraphNeighborsResponse,
    GraphPathRequest,
    GraphPathResponse,
    HealthResponse,
    MemoryDeleteResponse,
    MemoryGetResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStoreRequest,
    MemoryStoreResponse,
    StatsResponse,
)

__all__ = [
    # Schemas
    "HealthResponse",
    "MemoryStoreRequest",
    "MemoryStoreResponse",
    "MemorySearchRequest",
    "MemorySearchResponse",
    "MemoryGetResponse",
    "MemoryDeleteResponse",
    "StatsResponse",
    "GraphLinkRequest",
    "GraphLinkResponse",
    "GraphNeighborsRequest",
    "GraphNeighborsResponse",
    "GraphPathRequest",
    "GraphPathResponse",
    # Dependencies
    "auth_dep",
    "rate_limit_dep",
    "safe_parse_coord",
    "get_tenant_from_request",
    "get_tenant_scoped_namespace",
    "resolve_memory_type",
    "set_rate_limiter",
    "get_rate_limiter",
]
