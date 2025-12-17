# somafractalmemory/operations/graph_ops.py
"""Graph operations for SomaFractalMemory.

Extracted from core.py for VIBE compliance (<500 lines per file).
"""

import time
from typing import TYPE_CHECKING, Any

import structlog

from ..serialization import deserialize, serialize

if TYPE_CHECKING:
    from ..core import SomaFractalMemoryEnterprise

logger = structlog.get_logger()


def _coord_to_key(namespace: str, coord: tuple[float, ...]) -> tuple[str, str]:
    """Convert coordinate to KV store keys."""
    coord_str = repr(coord)
    data_key = f"{namespace}:{coord_str}:data"
    meta_key = f"{namespace}:{coord_str}:meta"
    return data_key, meta_key


def link_memories_op(
    system: "SomaFractalMemoryEnterprise",
    from_coord: tuple[float, ...],
    to_coord: tuple[float, ...],
    link_type: str = "related",
    weight: float | None = None,
) -> None:
    """Link two memories in the semantic graph."""
    from ..core import SomaFractalMemoryError

    lock = system.acquire_lock(f"lock:{from_coord}")
    if lock:
        with lock:
            data_key, _ = _coord_to_key(system.namespace, from_coord)
            data = system.kv_store.get(data_key)
            if not data:
                raise SomaFractalMemoryError(f"No memory at {from_coord}")
            try:
                value = deserialize(data)
            except Exception as exc:
                raise SomaFractalMemoryError(
                    f"Failed to deserialize memory at {from_coord}"
                ) from exc
            links = value.get("links", [])
            link_data = {"to": to_coord, "type": link_type, "timestamp": time.time()}
            if weight is not None:
                link_data["weight"] = weight
            links.append(link_data)
            value["links"] = links
            try:
                system.kv_store.set(data_key, serialize(value))
            except Exception:
                logger.warning(f"Failed to persist links for {data_key}")
            system.graph_store.add_link(from_coord, to_coord, link_data)


def get_linked_memories_op(
    system: "SomaFractalMemoryEnterprise",
    coord: tuple[float, ...],
    link_type: str | None = None,
    depth: int = 1,
) -> list[dict[str, Any]]:
    """Get memories linked to the given coordinate."""
    from .retrieve import retrieve_op

    neighbors = system.graph_store.get_neighbors(coord, link_type=link_type)
    out: list[dict[str, Any]] = []
    for c, _ in neighbors:
        if c:
            v = retrieve_op(system, c)
            if v:
                out.append(v)
    return out


def find_shortest_path_op(
    system: "SomaFractalMemoryEnterprise",
    from_coord: tuple[float, ...],
    to_coord: tuple[float, ...],
    link_type: str | None = None,
) -> list[Any]:
    """Find the shortest path between two coordinates in the semantic graph."""
    return system.graph_store.find_shortest_path(from_coord, to_coord, link_type)


def sync_graph_from_memories_op(system: "SomaFractalMemoryEnterprise") -> None:
    """Synchronize the graph store from all current memories.

    Design Decision (VIBE Compliant):
        The graph store (NetworkX) is intentionally ephemeral and rebuilt
        through normal memory operations. Graph links are created when:
        1. Memories are stored with explicit link metadata
        2. Co-recalled memories are linked via the API

        Full graph reconstruction from KV store is not implemented because:
        - It would require scanning all memories at startup (expensive)
        - Graph relationships are derived from usage patterns, not stored data
        - The graph is a performance optimization, not canonical data
    """
    pass
