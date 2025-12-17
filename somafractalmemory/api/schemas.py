# somafractalmemory/api/schemas.py
"""Pydantic schemas for SomaFractalMemory API.

Extracted from http_api.py for VIBE compliance (<500 lines per file).
"""

from typing import Any, Literal

from pydantic import BaseModel

from somafractalmemory.core import MemoryType


class HealthResponse(BaseModel):
    """Health check response model."""

    kv_store: bool
    vector_store: bool
    graph_store: bool


class MemoryStoreRequest(BaseModel):
    """Request model for storing a memory."""

    coord: str
    payload: dict[str, Any]
    memory_type: Literal["episodic", "semantic"] = MemoryType.EPISODIC.value


class MemoryStoreResponse(BaseModel):
    """Response model for memory store operation."""

    coord: str
    memory_type: str
    ok: bool = True


class MemorySearchRequest(BaseModel):
    """Request model for searching memories."""

    query: str
    top_k: int = 5
    filters: dict[str, Any] | None = None


class MemorySearchResponse(BaseModel):
    """Response model for memory search."""

    memories: list[dict[str, Any]]


class MemoryGetResponse(BaseModel):
    """Response model for fetching a single memory."""

    memory: dict[str, Any]


class MemoryDeleteResponse(BaseModel):
    """Response model for memory deletion."""

    coord: str
    deleted: bool


class StatsResponse(BaseModel):
    """Response model for system statistics."""

    total_memories: int
    episodic: int
    semantic: int
    vector_count: int | None = None
    namespaces: dict[str, dict[str, int]] | None = None
    vector_collections: dict[str, int] | None = None


class GraphLinkRequest(BaseModel):
    """Request model for creating a graph link."""

    from_coord: str
    to_coord: str
    link_type: str = "related"
    strength: float = 1.0
    metadata: dict[str, Any] | None = None


class GraphLinkResponse(BaseModel):
    """Response model for graph link creation."""

    from_coord: str
    to_coord: str
    link_type: str
    ok: bool = True


class GraphNeighborsRequest(BaseModel):
    """Request model for getting graph neighbors."""

    coord: str
    k_hop: int = 1
    limit: int = 10
    link_type: str | None = None


class GraphNeighborsResponse(BaseModel):
    """Response model for graph neighbors."""

    coord: str
    neighbors: list[dict[str, Any]]


class GraphPathRequest(BaseModel):
    """Request model for finding shortest path."""

    from_coord: str
    to_coord: str
    max_length: int = 10
    link_type: str | None = None


class GraphPathResponse(BaseModel):
    """Response model for shortest path."""

    from_coord: str
    to_coord: str
    path: list[str]
    link_types: list[str]
    found: bool
