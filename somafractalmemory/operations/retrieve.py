# somafractalmemory/operations/retrieve.py
"""Retrieve operations for SomaFractalMemory.

Extracted from core.py for VIBE compliance (<500 lines per file).
"""

import time
from typing import TYPE_CHECKING, Any, Optional

import structlog

from ..serialization import deserialize, serialize

if TYPE_CHECKING:
    from ..core import MemoryType, SomaFractalMemoryEnterprise

logger = structlog.get_logger()


def _coord_to_key(namespace: str, coord: tuple[float, ...]) -> tuple[str, str]:
    """Convert coordinate to KV store keys."""
    coord_str = repr(coord)
    data_key = f"{namespace}:{coord_str}:data"
    meta_key = f"{namespace}:{coord_str}:meta"
    return data_key, meta_key


def retrieve_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...],
) -> dict[str, Any] | None:
    """Retrieve a memory at the given coordinate."""
    lock = system.acquire_lock(f"lock:{coordinate}")
    if lock:
        with lock:
            data_key, _ = _coord_to_key(system.namespace, coordinate)
            data = system.kv_store.get(data_key)
            if not data:
                try:
                    for point in system.vector_store.scroll():
                        payload = getattr(point, "payload", {})
                        if isinstance(payload, dict) and payload.get("coordinate") == list(
                            coordinate
                        ):
                            return payload
                except Exception:
                    pass
                return None
            _, meta_key = _coord_to_key(system.namespace, coordinate)
            system.kv_store.hset(
                meta_key, mapping={b"last_accessed_timestamp": str(time.time()).encode("utf-8")}
            )
            try:
                value = deserialize(data)
            except Exception:
                logger.warning(f"Failed to deserialize memory at retrieve {data_key}")
                return None
            value["access_count"] = value.get("access_count", 0) + 1
            try:
                system.kv_store.set(data_key, serialize(value))
            except Exception:
                logger.warning(f"Failed to persist access_count for {data_key}")
            if system.cipher:
                for k in ["task", "code"]:
                    if k in value and value[k]:
                        try:
                            value[k] = system.cipher.decrypt(value[k].encode()).decode()
                        except Exception as e:
                            logger.warning(f"Decryption failed for key '{k}' in {coordinate}: {e}")
            return value
    return None


def retrieve_memories_op(
    system: "SomaFractalMemoryEnterprise",
    memory_type: Optional["MemoryType"] = None,
) -> list[dict[str, Any]]:
    """Retrieve all memories, optionally filtered by type."""
    all_mems = get_all_memories_op(system)
    if memory_type:
        return [m for m in all_mems if m.get("memory_type") == memory_type.value]
    return all_mems


def get_all_memories_op(system: "SomaFractalMemoryEnterprise") -> list[dict[str, Any]]:
    """Get all memories from the KV store."""
    memories: list[dict[str, Any]] = []
    pattern = f"{system.namespace}:*:data"
    for key in system.kv_store.scan_iter(pattern):
        try:
            data = system.kv_store.get(key)
            if data:
                try:
                    memories.append(deserialize(data))
                except Exception:
                    logger.warning(f"Failed to deserialize memory from key {key}")
        except Exception as e:
            logger.warning(f"Failed to load memory from key {key}: {e}")
    return memories


def save_version_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...],
) -> None:
    """Save a version snapshot of the memory at coordinate."""
    from ..core import SomaFractalMemoryError

    data_key, _ = _coord_to_key(system.namespace, coordinate)
    data = system.kv_store.get(data_key)
    if not data:
        raise SomaFractalMemoryError(f"No memory at {coordinate}")
    version_key = f"{data_key}:version:{time.time_ns()}"
    system.kv_store.set(version_key, data)


def get_versions_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...],
) -> list[dict[str, Any]]:
    """Get all version snapshots for a memory."""
    data_key, _ = _coord_to_key(system.namespace, coordinate)
    pattern = f"{data_key}:version:*"
    versions = []
    for vkey in system.kv_store.scan_iter(pattern):
        vdata = system.kv_store.get(vkey)
        if vdata:
            try:
                versions.append(deserialize(vdata))
            except Exception:
                logger.warning(f"Failed to deserialize version {vkey}")
    return versions


def iter_memories_op(system: "SomaFractalMemoryEnterprise", pattern: str | None = None):
    """Iterate over all memories."""
    try:
        for point in system.vector_store.scroll():
            try:
                yield point.payload
            except Exception:
                continue
    except Exception as e:
        logger.warning(
            f"Vector store unavailable for iter_memories: {e}, falling back to KV store."
        )
        if pattern is None:
            pattern = f"{system.namespace}:*:data"
        for key in system.kv_store.scan_iter(pattern):
            data = system.kv_store.get(key)
            if data:
                try:
                    yield deserialize(data)
                except Exception:
                    continue
