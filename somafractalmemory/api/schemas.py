# somafractalmemory/api/schemas.py
"""Pydantic schemas for SomaFractalMemory API.

100% Django + Pydantic patterns.
"""

from typing import Any, Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""

    kv_store: bool
    vector_store: bool
    graph_store: bool


class MemoryStoreRequest(BaseModel):
    """Request model for storing a memory."""

    coord: str
    payload: dict[str, Any]
    memory_type: Literal["episodic", "semantic"] = "episodic"


class MemoryStoreResponse(BaseModel):
    """Response model for storing a memory."""

    coord: str
    memory_type: str


class MemoryGetResponse(BaseModel):
    """Response model for getting a memory."""

    memory: dict[str, Any]


class MemoryDeleteResponse(BaseModel):
    """Response model for deleting a memory."""

    coord: str
    deleted: bool


class MemorySearchRequest(BaseModel):
    """Request model for searching memories."""

    query: str
    top_k: int = 5
    memory_type: str | None = None
    filters: dict[str, Any] | None = None


class MemorySearchResponse(BaseModel):
    """Response model for memory search results."""

    memories: list[dict[str, Any]]


class StatsResponse(BaseModel):
    """Response model for memory stats."""

    total_memories: int = 0
    episodic: int = 0
    semantic: int = 0
    namespace: str = ""


class TenantStats(BaseModel):
    """Stats for a single tenant."""

    tenant: str
    total_memories: int = 0
    episodic: int = 0
    semantic: int = 0
    graph_links: int = 0


class ServiceStatus(BaseModel):
    """Status of a backend service."""

    name: str
    healthy: bool
    latency_ms: float = 0.0
    details: dict[str, Any] | None = None


class DetailedHealthResponse(BaseModel):
    """Comprehensive health check with server details and tenant stats."""

    # Overall status
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    uptime_seconds: float

    # Backend services
    services: list[ServiceStatus]

    # Database stats
    database: dict[str, Any]

    # Per-tenant breakdown
    tenants: list[TenantStats]

    # System info
    system: dict[str, Any]


class GraphLinkRequest(BaseModel):
    """Request model for creating a graph link."""

    from_coord: str
    to_coord: str
    link_type: str | None = None
    strength: float = 1.0
    metadata: dict[str, Any] | None = None


class GraphLinkResponse(BaseModel):
    """Response model for graph link creation."""

    from_coord: str
    to_coord: str
    link_type: str
    ok: bool


class GraphNeighborsResponse(BaseModel):
    """Response model for graph neighbor query."""

    coord: str
    neighbors: list[dict[str, Any]]


class GraphPathResponse(BaseModel):
    """Response model for graph path query."""

    from_coord: str
    to_coord: str
    path: list[str]
    link_types: list[str]
    found: bool
