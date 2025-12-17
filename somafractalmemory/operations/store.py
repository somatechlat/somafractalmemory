# somafractalmemory/operations/store.py
"""Store operations for SomaFractalMemory.

Extracted from core.py for VIBE compliance (<500 lines per file).
"""

import json
import time
import uuid
from typing import TYPE_CHECKING, Any

import numpy as np
import structlog

from ..serialization import serialize

if TYPE_CHECKING:
    from ..core import MemoryType, SomaFractalMemoryEnterprise

logger = structlog.get_logger()


def _coord_to_key(namespace: str, coord: tuple[float, ...]) -> tuple[str, str]:
    """Convert coordinate to KV store keys."""
    coord_str = repr(coord)
    data_key = f"{namespace}:{coord_str}:data"
    meta_key = f"{namespace}:{coord_str}:meta"
    return data_key, meta_key


def store_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...],
    value: dict,
) -> None:
    """Store a value at the given coordinate in KV and vector stores."""
    data_key, meta_key = _coord_to_key(system.namespace, coordinate)
    try:
        system.kv_store.set(data_key, serialize(value))
    except Exception:
        try:
            system.kv_store.set(data_key, json.dumps(value).encode("utf-8"))
        except Exception:
            logger.warning(f"Failed to write memory for {data_key}")
    try:
        system.kv_store.hset(
            meta_key, mapping={b"creation_timestamp": str(time.time()).encode("utf-8")}
        )
    except Exception as e:
        logger.warning(f"Failed to set metadata for {meta_key}: {e}")

    try:
        vector = system.embed_text(json.dumps(value))
        system.vector_store.upsert(
            points=[
                {"id": str(uuid.uuid4()), "vector": vector.flatten().tolist(), "payload": value}
            ]
        )
    except Exception as e:
        logger.error(f"Vector store upsert failed: {e}")
        try:
            wal_key = f"{system.namespace}:wal:{uuid.uuid4()}"
            wal_payload = {
                "coordinate": list(coordinate),
                "value": value,
                "error": str(e),
                "ts": time.time(),
            }
            try:
                system.kv_store.set(wal_key, serialize(wal_payload))
            except Exception as e:
                logger.warning("Failed to write WAL entry", error=str(e))
        except Exception:
            pass


def store_memory_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...] | list[float],
    value: dict[str, Any],
    memory_type: "MemoryType",
) -> Any:
    """Store a memory record."""
    from common.config.settings import load_settings
    from common.utils.async_metrics import submit as _submit_metric

    from ..core import MemoryType as MT

    try:
        coord_t = tuple(coordinate)
    except Exception:
        coord_t = tuple([float(c) for c in coordinate])

    value = dict(value)
    value["memory_type"] = memory_type.value
    if memory_type == MT.EPISODIC:
        value["timestamp"] = value.get("timestamp", time.time())
    value["coordinate"] = list(coord_t)

    # Adaptive importance normalization
    raw_imp = value.get("importance", 1.0)
    try:
        raw_f = float(raw_imp)
    except Exception:
        raw_f = 0.0
    from .lifecycle import adaptive_importance_norm_op

    value["importance_norm"], system._imp_method = adaptive_importance_norm_op(system, raw_f)

    _settings = load_settings()
    _USE_ASYNC_METRICS = _settings.async_metrics_enabled

    def _maybe_submit(fn):
        if _USE_ASYNC_METRICS:
            try:
                _submit_metric(fn)
                return
            except Exception:
                pass
        try:
            fn()
        except Exception:
            pass

    with system.store_latency.labels(system.namespace).time():
        _maybe_submit(lambda: system.store_count.labels(system.namespace).inc())
        result = store_op(system, coord_t, value)

    if system.fast_core_enabled:
        try:
            emb = system.embed_text(json.dumps(value))
            _fast_append_op(
                system,
                emb,
                value.get("importance_norm", 0.0),
                value.get("timestamp", time.time()),
                value,
            )
        except Exception as e:
            logger.debug(f"Fast core append failed: {e}")

    system.graph_store.add_memory(coord_t, value)
    try:
        from .lifecycle import enforce_memory_limit_op

        enforce_memory_limit_op(system)
    except Exception as e:
        logger.debug(f"Memory limit enforcement failed: {e}")
    return result


def _fast_append_op(
    system: "SomaFractalMemoryEnterprise",
    vector: np.ndarray,
    importance_norm: float,
    ts: float,
    payload: dict[str, Any],
) -> None:
    """Append to fast core slabs."""
    if not system.fast_core_enabled:
        return
    if vector.shape[0] == 1:
        vector = vector[0]
    if system._fast_size >= system._fast_capacity:
        new_cap = system._fast_capacity * 2
        system._fast_vectors = np.vstack(
            [
                system._fast_vectors,
                np.zeros((system._fast_capacity, system.vector_dim), dtype="float32"),
            ]
        )
        system._fast_importance = np.concatenate(
            [system._fast_importance, np.zeros(system._fast_capacity, dtype="float32")]
        )
        system._fast_timestamps = np.concatenate(
            [system._fast_timestamps, np.zeros(system._fast_capacity, dtype="float64")]
        )
        system._fast_payloads.extend([None] * system._fast_capacity)
        system._fast_capacity = new_cap
    idx = system._fast_size
    system._fast_vectors[idx] = vector.astype("float32")
    system._fast_importance[idx] = float(importance_norm)
    system._fast_timestamps[idx] = ts
    system._fast_payloads[idx] = payload
    system._fast_size += 1


def store_memories_bulk_op(
    system: "SomaFractalMemoryEnterprise",
    items: list[tuple[tuple[float, ...], dict[str, Any], "MemoryType"]],
) -> bool:
    """Store multiple memories in bulk."""
    for coordinate, payload, memory_type in items:
        store_memory_op(system, coordinate, payload, memory_type)
    return True


def store_vector_only_op(
    system: "SomaFractalMemoryEnterprise",
    coordinate: tuple[float, ...],
    vector: np.ndarray,
    payload: dict | None = None,
) -> None:
    """Store only a vector without KV entry."""
    from ..core import SomaFractalMemoryError

    try:
        system.vector_store.upsert(
            points=[
                {
                    "id": str(uuid.uuid4()),
                    "vector": vector.flatten().tolist(),
                    "payload": payload or {"coordinate": list(coordinate)},
                }
            ]
        )
    except Exception as e:
        logger.error(f"Failed to store vector: {e}")
        raise SomaFractalMemoryError("Vector storage failed") from e


def export_memories_op(system: "SomaFractalMemoryEnterprise", path: str) -> int:
    """Export all memories to a JSONL file."""
    from .retrieve import get_all_memories_op

    mems = get_all_memories_op(system)
    with open(path, "w", encoding="utf-8") as f:
        for mem in mems:
            f.write(json.dumps(mem) + "\n")
    return len(mems)


def import_memories_op(
    system: "SomaFractalMemoryEnterprise",
    path: str,
    replace: bool = False,
) -> int:
    """Import memories from a JSONL file."""
    from ..core import MemoryType
    from .delete import delete_op

    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                mem = json.loads(line)
            except Exception:
                continue
            coord = mem.get("coordinate")
            if coord is None:
                continue
            coord_t = tuple(coord)
            mtype = (
                MemoryType.SEMANTIC
                if mem.get("memory_type") == MemoryType.SEMANTIC.value
                else MemoryType.EPISODIC
            )
            if replace:
                delete_op(system, coord_t)
            store_memory_op(system, coord_t, mem, memory_type=mtype)
            n += 1
    return n
