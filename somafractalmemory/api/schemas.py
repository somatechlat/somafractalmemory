# somafractalmemory/api/schemas.py
"""
SomaFractalMemory API Schemas - Pydantic Models
Copyright (C) 2025 SomaTech LAT.

100% Django + Pydantic patterns.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""

    kv_store: bool
    vector_store: bool
    graph_store: bool


class MemoryStoreRequest(BaseModel):
    """Request model for storing a memory.

    ``embedding`` is an optional precomputed vector (dim = SOMA_VECTOR_DIM /
    MEM_EMBED_DIM). When present it is stored verbatim; when absent the hash
    fallback embeds the payload and the record is flagged for lower ranking.
    ``tenant_id`` scopes the write (falls back to X-Soma-Tenant / auth tenant).
    """

    coord: str
    payload: dict[str, Any]
    memory_type: Literal["episodic", "semantic", "belief", "working_memory"] = "episodic"
    embedding: list[float] | None = None
    tenant_id: str | None = None
    # B20: importance must be a first-class column, not payload-only JSON.
    # Brain computes it (somabrain/api/memory/models.py) and sends it top-level.
    importance: float = Field(0.0, ge=0.0, le=1.0)
    # B19: belief semantics — a belief is not just a label.
    belief_confidence: float | None = Field(None, ge=0.0, le=1.0)
    belief_polarity: Literal["positive", "negative", "unknown"] | None = None


class MemoryStoreResponse(BaseModel):
    """Response model for storing a memory."""

    coord: str
    memory_type: str
    embedding_source: str = "hash"


class MemoryGetResponse(BaseModel):
    """Response model for getting a memory."""

    memory: dict[str, Any]


class MemoryDeleteResponse(BaseModel):
    """Response model for deleting a memory."""

    coord: str
    deleted: bool


class MemorySearchRequest(BaseModel):
    """Request model for searching memories.

    ``embedding`` is an optional precomputed query vector; when present it
    drives vector-similarity ranking. With only ``query`` text the query is
    embedded the same way as store (hash fallback).
    """

    query: str = ""
    # Bounded like somabrain/api/memory/models.py MemoryRecallRequest.top_k
    # (Field(3, ge=1, le=50)) — an unbounded top_k lets one request pull an
    # entire store into a response body. 200 is the house ceiling for a page.
    top_k: int = Field(5, ge=1, le=200)
    offset: int = Field(0, ge=0)
    memory_type: str | None = None
    filters: dict[str, Any] | None = None
    embedding: list[float] | None = None
    tenant_id: str | None = None


class MemorySearchResponse(BaseModel):
    """Response model for memory search results.

    ``degraded`` is mandatory honesty (stack lock): a vector-path failure must
    flag itself, never masquerade as a genuine empty result. Callers distinguish
    "no history" (degraded=False, memories=[]) from "store unavailable"
    (degraded=True).
    """

    memories: list[dict[str, Any]]
    degraded: bool = False
    degraded_reason: str | None = None


class StatsResponse(BaseModel):
    """Response model for memory stats.

    Counts cover every ``memory_type`` the store accepts
    (``episodic | semantic | belief``) — a kind that is stored but not
    counted is invisible, which is the defect this shape exists to prevent.
    """

    total_memories: int = 0
    episodic: int = 0
    semantic: int = 0
    belief: int = 0
    working_memory: int = 0
    namespace: str = ""


class TenantStats(BaseModel):
    """Stats for a single tenant."""

    tenant: str
    total_memories: int = 0
    episodic: int = 0
    semantic: int = 0
    belief: int = 0
    working_memory: int = 0
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
    """Response model for graph neighbor query.

    Each neighbour carries ``hops`` (distance from the seed) so k_hop is
    honest — a 2-hop result is distinguishable from a 1-hop result.
    """

    coord: str
    neighbors: list[dict[str, Any]]
    degraded: bool = False
    degraded_reason: str | None = None


class GraphPathResponse(BaseModel):
    """Response model for graph path query.

    ``found=False`` means no path exists. ``degraded=True`` means the store
    could not answer — the two must never look the same.
    """

    from_coord: str
    to_coord: str
    path: list[str]
    link_types: list[str]
    found: bool
    degraded: bool = False
    degraded_reason: str | None = None
