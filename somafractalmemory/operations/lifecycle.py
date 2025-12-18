# somafractalmemory/operations/lifecycle.py
"""Lifecycle operations for SomaFractalMemory.

Handles memory decay, consolidation, replay, and limit enforcement.
Extracted from core.py for VIBE compliance (<500 lines per file).
"""

import math
import time
from typing import TYPE_CHECKING, Any

import numpy as np
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


def decay_memories_op(system: "SomaFractalMemoryEnterprise") -> None:
    """Periodic background task that applies basic decay rules to memories."""
    while True:
        now = time.time()
        try:
            iterator = system.kv_store.scan_iter(f"{system.namespace}:*:meta")
        except Exception as e:
            logger.warning(f"Error enumerating keys for decay: {e}")
            time.sleep(system.pruning_interval_seconds)
            continue

        try:
            for meta_key in iterator:
                try:
                    metadata = system.kv_store.hgetall(meta_key)
                    created = float(metadata.get(b"creation_timestamp", b"0"))
                    age = now - created
                    data_key = meta_key.replace(":meta", ":data")
                    raw_data = system.kv_store.get(data_key)
                    if not raw_data:
                        continue
                    try:
                        memory_item = deserialize(raw_data)
                    except Exception:
                        logger.warning(f"Failed to deserialize memory {data_key} during decay")
                        continue
                    for i, threshold in enumerate(system.decay_thresholds_seconds):
                        if age > threshold:
                            keys_to_remove = (
                                set(system.decayable_keys_by_level[i])
                                if i < len(system.decayable_keys_by_level)
                                else set()
                            )
                            for key in keys_to_remove:
                                memory_item.pop(key, None)
                    try:
                        system.kv_store.set(data_key, serialize(memory_item))
                    except Exception:
                        logger.warning(f"Failed to write decayed memory {data_key}")
                except Exception as e:
                    logger.warning(f"Error during decay for {meta_key}: {e}")
        except Exception as e:
            logger.warning(f"Error iterating keys for decay: {e}")
            time.sleep(system.pruning_interval_seconds)
            continue
        time.sleep(system.pruning_interval_seconds)


def apply_decay_to_all_op(system: "SomaFractalMemoryEnterprise") -> None:
    """Apply advanced memory decay check to all memories."""
    logger.debug("Applying advanced memory decay check...")
    now = time.time()
    try:
        iterator = system.kv_store.scan_iter(f"{system.namespace}:*:meta")
    except Exception as e:
        logger.warning(f"Error enumerating keys for run_decay_once: {e}")
        return

    for meta_key in iterator:
        try:
            metadata = system.kv_store.hgetall(meta_key)
            created = float(metadata.get(b"creation_timestamp", b"0"))
            age = now - created
            last_accessed = float(metadata.get(b"last_accessed_timestamp", created))
            recency = now - last_accessed
            data_key = meta_key.replace(":meta", ":data")
            raw_data = system.kv_store.get(data_key)
            if not raw_data:
                continue
            try:
                memory_item = deserialize(raw_data)
            except Exception:
                logger.warning(f"Failed to deserialize memory {data_key} in advanced decay")
                continue
            access_count = memory_item.get("access_count", 0)
            importance = memory_item.get("importance", 0)

            w_age = float(getattr(system, "_decay_w_age", 1.0))
            w_rec = float(getattr(system, "_decay_w_recency", 1.0))
            w_acc = float(getattr(system, "_decay_w_access", 0.5))
            w_imp = float(getattr(system, "_decay_w_importance", 2.0))
            threshold = float(getattr(system, "_decay_threshold", 2.0))

            decay_score = (
                (w_age * (age / 3600))
                + (w_rec * (recency / 3600))
                - (w_acc * access_count)
                - (w_imp * importance)
            )
            if decay_score > threshold and importance <= 1:
                keys_to_remove = set(memory_item.keys()) - {
                    "memory_type",
                    "timestamp",
                    "coordinate",
                    "importance",
                }
                for key in keys_to_remove:
                    memory_item.pop(key, None)
                try:
                    system.kv_store.set(data_key, serialize(memory_item))
                except Exception:
                    logger.warning(f"Failed to write advanced-decayed memory {data_key}")
        except Exception as e:
            logger.warning(f"Error during advanced decay for {meta_key}: {e}")


def run_decay_once_op(system: "SomaFractalMemoryEnterprise") -> None:
    """Run a single decay pass over all memories."""
    now = time.time()
    for meta_key in system.kv_store.scan_iter(f"{system.namespace}:*:meta"):
        try:
            metadata = system.kv_store.hgetall(meta_key)
            created = float(metadata.get(b"creation_timestamp", b"0"))
            age = now - created
            data_key = meta_key.replace(":meta", ":data")
            raw_data = system.kv_store.get(data_key)
            if not raw_data:
                continue
            try:
                memory_item = deserialize(raw_data)
            except Exception:
                logger.warning(f"Failed to deserialize memory {data_key} in run_decay_once")
                continue
            for i, threshold in enumerate(system.decay_thresholds_seconds):
                if age > threshold:
                    keys_to_remove = set(system.decayable_keys_by_level[i])
                    for key in keys_to_remove:
                        memory_item.pop(key, None)
            try:
                system.kv_store.set(data_key, serialize(memory_item))
            except Exception:
                logger.warning(f"Failed to persist decayed memory {data_key}")
        except Exception as e:
            logger.warning(f"Error during run_decay_once for {meta_key}: {e}")


def consolidate_memories_op(
    system: "SomaFractalMemoryEnterprise", window_seconds: int = 3600
) -> None:
    """Consolidate recent episodic memories into semantic memories."""
    from ..core import MemoryType
    from .retrieve import retrieve_memories_op
    from .store import store_memory_op

    now = time.time()
    episodic = retrieve_memories_op(system, MemoryType.EPISODIC)
    for mem in episodic:
        if now - mem.get("timestamp", 0) < window_seconds:
            coord_val = mem.get("coordinate")
            if coord_val:
                coord_t = tuple(coord_val)
                summary = {
                    "fact": f"Summary of event at {mem.get('timestamp')}",
                    "source_coord": coord_val,
                    "memory_type": MemoryType.SEMANTIC.value,
                    "consolidated_from": list(coord_t),
                    "timestamp": now,
                }
                store_memory_op(system, coord_t, summary, memory_type=MemoryType.SEMANTIC)


def replay_memories_op(
    system: "SomaFractalMemoryEnterprise",
    n: int = 5,
    memory_type: "MemoryType" = None,
) -> list[dict[str, Any]]:
    """Replay random memories of the given type."""
    import random

    from ..core import MemoryType as MT
    from .retrieve import retrieve_memories_op

    if memory_type is None:
        memory_type = MT.EPISODIC
    mems = retrieve_memories_op(system, memory_type)
    return random.sample(mems, min(n, len(mems)))


def reflect_op(
    system: "SomaFractalMemoryEnterprise",
    n: int = 5,
    memory_type: "MemoryType" = None,
) -> list[dict[str, Any]]:
    """Reflect on memories with hook callbacks."""
    from ..core import MemoryType as MT

    if memory_type is None:
        memory_type = MT.EPISODIC
    system._call_hook("before_reflect", n, memory_type)
    memories = replay_memories_op(system, n=n, memory_type=memory_type)
    system._call_hook("after_reflect", n, memory_type, memories)
    return memories


def enforce_memory_limit_op(system: "SomaFractalMemoryEnterprise") -> None:
    """Enforce the maximum memory limit by pruning low-importance memories."""
    all_items = []
    for meta_key in system.kv_store.scan_iter(f"{system.namespace}:*:meta"):
        try:
            metadata = system.kv_store.hgetall(meta_key)
            created = float(metadata.get(b"creation_timestamp", b"0"))
            data_key = meta_key.replace(":meta", ":data")
            raw_data = system.kv_store.get(data_key)
            if not raw_data:
                continue
            try:
                mem = deserialize(raw_data)
            except Exception:
                continue
            imp = int(mem.get("importance", 0))
            all_items.append((imp, created, data_key, meta_key))
        except Exception:
            continue
    excess = max(0, len(all_items) - int(system.max_memory_size))
    if excess <= 0:
        return
    all_items.sort(key=lambda t: (t[0], t[1]))
    for _, _, data_key, meta_key in all_items[:excess]:
        try:
            system.kv_store.delete(data_key)
            system.kv_store.delete(meta_key)
        except Exception:
            continue


def adaptive_importance_norm_op(
    system: "SomaFractalMemoryEnterprise", raw: float
) -> tuple[float, str]:
    """Compute adaptive importance normalization."""
    system._imp_reservoir.append(raw)
    if len(system._imp_reservoir) > int(getattr(system, "_imp_reservoir_max", 512)):
        system._imp_reservoir.pop(0)

    n = len(system._imp_reservoir)

    if system._importance_min is None or raw < system._importance_min:
        system._importance_min = raw
    if system._importance_max is None or raw > system._importance_max:
        system._importance_max = raw

    stride = int(getattr(system, "_imp_stride", 64))
    if n < stride:
        span = (system._importance_max - system._importance_min) or 1.0
        return ((raw - system._importance_min) / span, "minmax")

    if (n - system._imp_last_recompute) >= stride or system._imp_q10 is None:
        arr = np.array(system._imp_reservoir, dtype="float64")
        system._imp_q10, system._imp_q50, system._imp_q90, system._imp_q99 = np.percentile(
            arr, [10, 50, 90, 99]
        )
        system._imp_last_recompute = n

    q10 = system._imp_q10 or raw
    q50 = system._imp_q50 or raw
    q90 = system._imp_q90 or raw
    q99 = system._imp_q99 or raw
    eps = 1e-12
    upper_core = (q90 - q50) or eps
    lower_core = (q50 - q10) or eps
    R_tail_max = (system._importance_max - q90) / upper_core
    R_tail_ext = (q99 - q90) / upper_core
    R_asym = (q90 - q50) / lower_core

    if R_tail_max <= 5 and R_asym <= 3:
        span = (system._importance_max - system._importance_min) or 1.0
        norm = (raw - system._importance_min) / span
        return (max(0.0, min(1.0, norm)), "minmax")
    elif R_tail_max <= 15 and R_tail_ext <= 8:
        spread = (q90 - q10) or 1.0
        delta = float(getattr(system, "_imp_winsor_delta", 0.25)) * spread
        L = max(system._importance_min, q10 - delta)
        U = min(system._importance_max, q90 + delta)
        if U - L < eps:
            return (0.5, "winsor")
        clipped = min(max(raw, L), U)
        return ((clipped - L) / (U - L), "winsor")
    else:
        spread = q90 - q10
        if spread < eps:
            return (0.5, "logistic")
        target = float(getattr(system, "_imp_logit_target_ratio", 9.0))
        k = math.log(target) / spread
        c = q50
        k_max = float(getattr(system, "_imp_logit_k_max", 25.0))
        if k > k_max:
            k = k_max
        try:
            norm = 1.0 / (1.0 + math.exp(-k * (raw - c)))
        except OverflowError:
            norm = 1.0 if raw > c else 0.0
        return (norm, "logistic")


def reconcile_once_op(system: "SomaFractalMemoryEnterprise") -> None:
    """Reconcile uncommitted WAL entries by marking them as committed."""
    wal_prefix = f"{system.namespace}:wal:"
    for wal_key in system.kv_store.scan_iter(f"{wal_prefix}*"):
        raw = system.kv_store.get(wal_key)
        if not raw:
            continue
        try:
            entry = deserialize(raw)
        except Exception:
            continue
        if entry.get("status") != "committed":
            entry["status"] = "committed"
            try:
                system.kv_store.set(wal_key, serialize(entry))
            except Exception:
                pass
