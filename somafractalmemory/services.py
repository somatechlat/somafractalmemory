"""Compatibility exports for service-layer imports.

Code is the source of truth, but external integrations (and older docs) expect:
    from somafractalmemory.services import MemoryService

The canonical implementations live under `somafractalmemory.admin.core.services`.
"""

from somafractalmemory.admin.core.services import (  # noqa: F401
    GraphService,
    MemoryService,
    get_graph_service,
    get_memory_service,
)

__all__ = [
    "MemoryService",
    "GraphService",
    "get_memory_service",
    "get_graph_service",
]
