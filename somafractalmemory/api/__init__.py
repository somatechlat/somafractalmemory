"""SomaFractalMemory API - 100% Django + Django Ninja.

All endpoints use Django Ninja routers.
All strings use centralized messages for i18n.
"""

# Re-export core components
from .core import (
    API_TOKEN,
    api,
    get_graph,
    get_mem,
    get_rate_limiter,
)

# Re-export messages
from .messages import (
    ErrorCode,
    SuccessCode,
    get_message,
)

# Re-export schemas
from .schemas import (
    GraphLinkRequest,
    GraphLinkResponse,
    GraphNeighborsResponse,
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
    # Core
    "api",
    "get_mem",
    "get_graph",
    "get_rate_limiter",
    "API_TOKEN",
    # Messages
    "SuccessCode",
    "ErrorCode",
    "get_message",
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
    "GraphNeighborsResponse",
    "GraphPathResponse",
]
