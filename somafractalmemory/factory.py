# Standard library imports
import os
from collections.abc import Iterator, Mapping
from enum import Enum
from typing import Any

from common.config.settings import load_settings

# Local application imports (alphabetical)
from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.storage import (
    InMemoryVectorStore,
    PostgresKeyValueStore,
    QdrantVectorStore,
    RedisKeyValueStore,
)
from somafractalmemory.interfaces.storage import IKeyValueStore


class PostgresRedisHybridStore(IKeyValueStore):
    """Combine a PostgresKeyValueStore (canonical) with a RedisKeyValueStore.

    * ``set`` writes to both stores.
    * ``get`` tries Redis first (cache hit) and falls back to Postgres.
    * ``delete`` removes from both.
    * ``scan_iter`` merges keys from both stores, deduplicating.
    * ``hgetall`` / ``hset`` prefer Postgres, but also keep Redis in sync.
    * ``lock`` uses Redis if available, otherwise falls back to the Postgres
      store's simple in‑process lock.
    * ``health_check`` requires both backends to be healthy.
    """

    def __init__(
        self, pg_store: PostgresKeyValueStore, redis_store: RedisKeyValueStore | None = None
    ):
        self.pg_store = pg_store
        self.redis_store = redis_store

    # ----- Basic KV operations ------------------------------------------------
    def set(self, key: str, value: bytes):
        # Write to Postgres (canonical) first; then cache in Redis if present.
        self.pg_store.set(key, value)
        if self.redis_store:
            self.redis_store.set(key, value)

    def get(self, key: str) -> bytes | None:
        # Try Redis cache first for speed.
        if self.redis_store:
            cached = self.redis_store.get(key)
            if cached is not None:
                return cached
        # Fallback to Postgres.
        return self.pg_store.get(key)

    def delete(self, key: str):
        self.pg_store.delete(key)
        if self.redis_store:
            self.redis_store.delete(key)

    # ----- Iteration & hash helpers ------------------------------------------
    def scan_iter(self, pattern: str) -> Iterator[str]:
        seen: set[str] = set()
        for k in self.pg_store.scan_iter(pattern):
            seen.add(k)
            yield k
        if self.redis_store:
            for k in self.redis_store.scan_iter(pattern):
                if k not in seen:
                    seen.add(k)
                    yield k

    def hgetall(self, key: str) -> dict[bytes, bytes]:
        # Prefer Postgres (authoritative) but fall back to Redis.
        pg_val = self.pg_store.hgetall(key)
        if pg_val:
            return pg_val
        if self.redis_store:
            return self.redis_store.hgetall(key)
        return {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        # Write to both stores to keep cache in sync.
        self.pg_store.hset(key, mapping)
        if self.redis_store:
            self.redis_store.hset(key, mapping)

    # ----- Lock & health ------------------------------------------------------
    def lock(self, name: str, timeout: int = 10):
        if self.redis_store:
            return self.redis_store.lock(name, timeout)
        return self.pg_store.lock(name, timeout)

    def health_check(self) -> bool:
        ok = self.pg_store.health_check()
        if self.redis_store:
            ok = ok and self.redis_store.health_check()
        return ok


class MemoryMode(Enum):
    """Single supported memory mode."""

    EVENTED_ENTERPRISE = "evented_enterprise"

    @classmethod
    def from_string(cls, value: str | None) -> "MemoryMode":
        key = (value or cls.EVENTED_ENTERPRISE.value).strip().lower()
        if key != cls.EVENTED_ENTERPRISE.value:
            raise ValueError(
                f"Unsupported memory mode '{value}'. Only '{cls.EVENTED_ENTERPRISE.value}' is supported."
            )
        return cls.EVENTED_ENTERPRISE


def create_memory_system(
    mode: MemoryMode, namespace: str, config: dict[str, Any] | None = None
) -> SomaFractalMemoryEnterprise:
    """
    Factory function to create a SomaFractalMemoryEnterprise instance based on the specified mode.

    Parameters
    ----------
    mode : MemoryMode
        Must be ``MemoryMode.EVENTED_ENTERPRISE``.
    namespace : str
        The namespace for the memory system.
    config : Optional[Dict[str, Any]]
        Optional configuration dictionary for backend setup.

    Returns
    -------
    SomaFractalMemoryEnterprise
        Configured memory system instance.
    """
    # If no explicit config dict is provided, load service settings from the
    # centralised Pydantic settings and populate a small config mapping so the
    # rest of the factory can remain unchanged.
    if config is None:
        settings = load_settings()
        # Map known infra endpoints into the expected config shape. We keep this
        # conservative: only populate host fields which downstream stores can use.
        config = {
            "redis": {"host": getattr(settings.infra, "redis", None)},
            "postgres": {"url": getattr(settings, "postgres_url", None)},
            "qdrant": {"host": getattr(settings, "qdrant_host", None)},
            "memory_enterprise": {},
        }
    else:
        config = config or {}
    kv_store = None
    vector_store = None
    graph_store = None

    enterprise_cfg = config.get("memory_enterprise", {})

    if mode != MemoryMode.EVENTED_ENTERPRISE:
        raise ValueError(
            f"Unsupported memory mode: {mode}. Only '{MemoryMode.EVENTED_ENTERPRISE.value}' is supported."
        )

    redis_cfg = dict(config.get("redis", {}))
    postgres_cfg = dict(config.get("postgres", {}))
    qdrant_cfg = dict(config.get("qdrant", {}))

    # Redis store configuration – default to testing stub when no host/port provided.
    redis_testing = bool(redis_cfg.pop("testing", False))
    if redis_cfg:
        # Retain only supported kwargs
        redis_kwargs = {k: redis_cfg[k] for k in ("host", "port", "db") if k in redis_cfg}
    else:
        redis_kwargs = {}
    if redis_testing or not redis_kwargs:
        redis_store = RedisKeyValueStore(testing=True)
    else:
        redis_store = RedisKeyValueStore(**redis_kwargs)

    # Optional Postgres primary store
    pg_url = postgres_cfg.get("url")
    pg_store = PostgresKeyValueStore(url=pg_url) if pg_url else None

    if pg_store and redis_store:
        kv_store = PostgresRedisHybridStore(pg_store=pg_store, redis_store=redis_store)
    elif pg_store:
        kv_store = pg_store
    else:
        kv_store = redis_store

    # Vector store selection – support explicit Qdrant config, otherwise fall back to in-memory.
    vector_cfg = config.get("vector", {})
    vector_backend = (vector_cfg.get("backend") or "").strip().lower()
    use_memory_vectors = vector_backend == "memory" or qdrant_cfg.pop("testing", False)

    if not qdrant_cfg:
        # Provide sane defaults when nothing supplied.
        qdrant_cfg = {"url": os.getenv("QDRANT_URL", "http://quadrant:8080")}

    if use_memory_vectors:
        vector_store = InMemoryVectorStore()
    else:
        vector_store = QdrantVectorStore(collection_name=namespace, **qdrant_cfg)

    graph_store = NetworkXGraphStore()
    eventing_enabled = config.get("eventing", {}).get("enabled", True)

    memory = SomaFractalMemoryEnterprise(
        namespace=namespace,
        kv_store=kv_store,
        vector_store=vector_store,
        graph_store=graph_store,
        max_memory_size=enterprise_cfg.get("max_memory_size", 100000),
        pruning_interval_seconds=enterprise_cfg.get("pruning_interval_seconds", 600),
        decay_thresholds_seconds=enterprise_cfg.get("decay_thresholds_seconds", []),
        decayable_keys_by_level=enterprise_cfg.get("decayable_keys_by_level", []),
        decay_enabled=enterprise_cfg.get("decay_enabled", True),
        reconcile_enabled=enterprise_cfg.get("reconcile_enabled", True),
    )
    # Expose the event‑publishing toggle on the memory instance.
    memory.eventing_enabled = eventing_enabled
    return memory
