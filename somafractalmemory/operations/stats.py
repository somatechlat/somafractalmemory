# somafractalmemory/operations/stats.py
"""Statistics and health operations for SomaFractalMemory.

Extracted from core.py for VIBE compliance (<500 lines per file).
"""

import json
import time
from typing import TYPE_CHECKING, Any, Optional

import structlog

from common.config.settings import load_settings

from ..serialization import deserialize

if TYPE_CHECKING:
    from ..core import MemoryType, SomaFractalMemoryEnterprise

logger = structlog.get_logger()
_settings = load_settings()


def memory_stats_op(system: "SomaFractalMemoryEnterprise") -> dict[str, Any]:
    """Get memory statistics."""
    from ..core import MemoryType

    try:
        try:
            from psycopg2.sql import SQL, Identifier
        except Exception:
            SQL = None
            Identifier = None

        kv_count = None
        episodic = 0
        semantic = 0
        data_like = f"{system.namespace}:%:data"

        pg_store = None
        if hasattr(system.kv_store, "pg_store") and system.kv_store.pg_store is not None:
            pg_store = system.kv_store.pg_store

        if pg_store is not None and SQL is not None:

            def _count(cur):
                cur.execute(
                    SQL("SELECT COUNT(*) FROM {} WHERE key LIKE %s;").format(
                        Identifier(pg_store._TABLE_NAME)
                    ),
                    (data_like,),
                )
                return cur.fetchone()[0]

            kv_count = int(pg_store._execute(_count) or 0)

            def _fetch(cur):
                cur.execute(
                    SQL("SELECT value FROM {} WHERE key LIKE %s;").format(
                        Identifier(pg_store._TABLE_NAME)
                    ),
                    (data_like,),
                )
                return [r[0] for r in cur.fetchall()]

            rows = pg_store._execute(_fetch)
            for val in rows:
                if isinstance(val, dict):
                    mt = val.get("memory_type")
                    if mt == MemoryType.EPISODIC.value:
                        episodic += 1
                    elif mt == MemoryType.SEMANTIC.value:
                        semantic += 1
        else:
            glob_pattern = f"{system.namespace}:*:data"
            keys = set(system.kv_store.scan_iter(glob_pattern))
            kv_count = len(keys)
            for key in keys:
                raw = system.kv_store.get(key)
                if not raw:
                    continue
                try:
                    obj = deserialize(raw)
                except Exception:
                    continue
                mt = obj.get("memory_type")
                if mt == MemoryType.EPISODIC.value:
                    episodic += 1
                elif mt == MemoryType.SEMANTIC.value:
                    semantic += 1

        # Get vector count from the namespace's collection only (namespace isolation)
        vector_count = 0
        try:
            if hasattr(system.vector_store, "count"):
                # Use efficient count() method - returns only this namespace's vectors
                vector_count = system.vector_store.count()
            elif hasattr(system.vector_store, "scroll"):
                # Fallback to scroll if count() not available
                for _ in system.vector_store.scroll():
                    vector_count += 1
        except Exception as e:
            logger.warning("Failed to get vector count", error=str(e))
            vector_count = 0

        # Build namespace stats for current namespace only (namespace isolation)
        namespaces: dict[str, dict[str, int]] = {
            system.namespace: {
                "total": int(kv_count or 0),
                "episodic": int(episodic),
                "semantic": int(semantic),
            }
        }

        if not kv_count:
            try:
                glob_pattern = f"{system.namespace}:*:data"
                kv_count = len(list(system.kv_store.scan_iter(glob_pattern)))
            except Exception:
                kv_count = 0

        return {
            "total_memories": int(kv_count or 0),
            "episodic": int(episodic),
            "semantic": int(semantic),
            "vector_count": int(vector_count),
            "namespaces": namespaces,
        }
    except Exception:
        from .retrieve import get_all_memories_op

        all_mems = get_all_memories_op(system)
        return {
            "total_memories": len(all_mems),
            "episodic": sum(
                1 for m in all_mems if m.get("memory_type") == MemoryType.EPISODIC.value
            ),
            "semantic": sum(
                1 for m in all_mems if m.get("memory_type") == MemoryType.SEMANTIC.value
            ),
        }


def summarize_memories_op(
    system: "SomaFractalMemoryEnterprise",
    n: int = 10,
    memory_type: Optional["MemoryType"] = None,
) -> list[str]:
    """Get summaries of recent memories."""
    from .retrieve import retrieve_memories_op

    mems = retrieve_memories_op(system, memory_type)
    mems = sorted(mems, key=lambda m: m.get("timestamp", 0), reverse=True)[:n]
    return [str(m.get("task", m.get("fact", "<no summary>"))) for m in mems]


def get_recent_op(
    system: "SomaFractalMemoryEnterprise",
    n: int = 10,
    memory_type: Optional["MemoryType"] = None,
) -> list[dict[str, Any]]:
    """Get the most recent memories."""
    from .retrieve import retrieve_memories_op

    mems = retrieve_memories_op(system, memory_type)
    return sorted(mems, key=lambda m: m.get("timestamp", 0), reverse=True)[:n]


def get_important_op(
    system: "SomaFractalMemoryEnterprise",
    n: int = 10,
    memory_type: Optional["MemoryType"] = None,
) -> list[dict[str, Any]]:
    """Get the most important memories."""
    from .retrieve import retrieve_memories_op

    mems = retrieve_memories_op(system, memory_type)
    return sorted(mems, key=lambda m: m.get("importance", 0), reverse=True)[:n]


def health_check_op(system: "SomaFractalMemoryEnterprise") -> dict[str, bool]:
    """Check health of all stores."""

    def safe(check):
        try:
            return bool(check())
        except Exception:
            return False

    return {
        "kv_store": safe(system.kv_store.health_check),
        "vector_store": safe(system.vector_store.health_check),
        "graph_store": safe(system.graph_store.health_check),
    }


def audit_log_op(
    system: "SomaFractalMemoryEnterprise",
    action: str,
    coordinate: tuple,
    user: str = "system",
) -> None:
    """Write an audit log entry."""
    log_entry = {
        "action": action,
        "coordinate": coordinate,
        "user": user,
        "timestamp": time.time(),
    }
    with open("audit_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
