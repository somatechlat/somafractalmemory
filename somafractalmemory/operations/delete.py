# somafractalmemory/operations/delete.py
"""Delete operations for SomaFractalMemory.

Extracted from core.py for VIBE compliance (<500 lines per file).
"""

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from ..core import SomaFractalMemoryEnterprise

logger = structlog.get_logger()


def _coord_to_key(namespace: str, coord: tuple[float, ...]) -> tuple[str, str]:
    """Convert coordinate to KV store keys."""
    coord_str = repr(coord)
    data_key = f"{namespace}:{coord_str}:data"
    meta_key = f"{namespace}:{coord_str}:meta"
    return data_key, meta_key


def delete_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...],
) -> bool:
    """Delete a memory at the given coordinate from all stores."""
    from ..core import KeyValueStoreError, VectorStoreError

    data_key, meta_key = _coord_to_key(system.namespace, coordinate)

    try:
        system.kv_store.delete(data_key)
        system.kv_store.delete(meta_key)
    except Exception as exc:
        raise KeyValueStoreError(str(exc)) from exc

    try:
        remove_vector_entries_op(system, coordinate)
    except VectorStoreError:
        logger.error("Vector store delete failed for coordinate %s", coordinate, exc_info=True)
        raise

    system.graph_store.remove_memory(coordinate)
    return True


def remove_vector_entries_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...],
) -> None:
    """Delete vector points that reference the given coordinate."""
    ids_to_remove: list[str] = []
    try:
        for point in system.vector_store.scroll():
            payload = getattr(point, "payload", {})
            if isinstance(payload, dict) and payload.get("coordinate") == list(coordinate):
                pid = getattr(point, "id", None)
                if pid:
                    ids_to_remove.append(str(pid))
    except Exception:
        ids_to_remove = []

    if ids_to_remove:
        try:
            system.vector_store.delete(ids_to_remove)
        except Exception as exc:
            logger.warning("Failed to delete vector entries during memory delete", error=str(exc))


def forget_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...],
) -> None:
    """Forget (delete) a memory with hook callbacks."""
    system._call_hook("before_forget", coordinate)
    delete_op(system, coordinate)
    system._call_hook("after_forget", coordinate)


def delete_many_op(
    system: "SomaFractalMemoryEnterprise",
    coordinates: list[tuple[float, ...]],
) -> int:
    """Delete multiple memories by coordinate."""
    count = 0
    for coord in coordinates:
        data_key, _ = _coord_to_key(system.namespace, coord)
        if system.kv_store.get(data_key):
            delete_op(system, coord)
            count += 1
    return count
