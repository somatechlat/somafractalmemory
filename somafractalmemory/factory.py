# Standard library imports
from enum import Enum
from typing import Any, Dict, Iterator, Mapping, Optional

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

    def get(self, key: str) -> Optional[bytes]:
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

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
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
    """
    Enum for supported memory system modes (v2).

    Modes:
    - DEVELOPMENT: Local development (default).
    - TEST: CI/test mode with in-memory components.
    - EVENTED_ENTERPRISE: Production event-driven mode (Kafka + Postgres + Qdrant).
    - CLOUD_MANAGED: Alias for EVENTED_ENTERPRISE using managed services.
    - LEGACY_COMPAT: Hidden compatibility mode for short-term migration.
    """

    DEVELOPMENT = "development"
    TEST = "test"
    EVENTED_ENTERPRISE = "evented_enterprise"
    CLOUD_MANAGED = "cloud_managed"
    # LEGACY_COMPAT removed — project is v2 JSON-first only.


# Note: legacy aliases were intentionally removed for v2. Callers should use
# the canonical v2 mode names (DEVELOPMENT, TEST, EVENTED_ENTERPRISE,
# CLOUD_MANAGED). This module enforces the new names to avoid ambiguity.


# Backwards-compatible aliases for older enum names used in tests and existing code.
# These provide a short-term compatibility shim so tests referencing the previous
# names (e.g. LOCAL_AGENT, ON_DEMAND, ENTERPRISE) do not immediately break.
# Keep this shim small and temporary — it's better to update callers to the new
# v2 mode names in follow-up work.
# Map the historical LOCAL_AGENT to LEGACY_COMPAT so older behavior (WAL format,
# storage expectations) remains available for tests and short-term compatibility.
# Legacy aliases removed — project is v2 JSON-first only.


def create_memory_system(
    mode: MemoryMode, namespace: str, config: Optional[Dict[str, Any]] = None
) -> SomaFractalMemoryEnterprise:
    """
    Factory function to create a SomaFractalMemoryEnterprise instance based on the specified mode.

    Parameters
    ----------
    mode : MemoryMode
        The mode to use (ON_DEMAND, LOCAL_AGENT, ENTERPRISE).
    namespace : str
        The namespace for the memory system.
    config : Optional[Dict[str, Any]]
        Optional configuration dictionary for backend setup.

    Returns
    -------
    SomaFractalMemoryEnterprise
        Configured memory system instance.
    """
    config = config or {}
    kv_store = None
    vector_store = None
    graph_store = None

    vector_cfg = config.get("vector", {})
    enterprise_cfg = config.get("memory_enterprise", {})

    # ------------------------------------------------------------
    # Development mode – local development with optional Redis cache.
    # ------------------------------------------------------------
    if mode == MemoryMode.DEVELOPMENT:
        # Redis configuration (may include testing flag)
        redis_cfg = config.get("redis", {})
        redis_enabled = redis_cfg.get("enabled", True)
        redis_store = RedisKeyValueStore(**redis_cfg) if redis_cfg and redis_enabled else None

        # PostgreSQL configuration – optional. If a URL is provided we create a Postgres store,
        # otherwise we fall back to using the Redis store directly (or an in‑memory stub).
        postgres_cfg = config.get("postgres", {})
        pg_url = postgres_cfg.get("url")
        if pg_url:
            pg_store = PostgresKeyValueStore(url=pg_url)
        else:
            pg_store = None

        # Combine stores only when both are present; otherwise use the available one.
        if pg_store and redis_store:
            kv_store = PostgresRedisHybridStore(pg_store=pg_store, redis_store=redis_store)
        elif redis_store:
            kv_store = redis_store
        elif pg_store:
            kv_store = pg_store
        else:
            # As a last resort use an in‑memory KV store (Redis in testing mode).
            kv_store = RedisKeyValueStore(testing=True)

        # Vector store selection (Qdrant or in‑memory)
        qdrant_cfg = config.get("qdrant", {})
        if vector_cfg.get("backend") == "qdrant" or qdrant_cfg.get("path"):
            qconf = qdrant_cfg if qdrant_cfg else {"location": ":memory:"}
            vector_store = QdrantVectorStore(collection_name=namespace, **qconf)
        else:
            vector_store = InMemoryVectorStore()
        graph_store = NetworkXGraphStore()

        # Event‑publishing flag – default to True.
        eventing_enabled = config.get("eventing", {}).get("enabled", True)

    # ------------------------------------------------------------
    # Test mode – deterministic in‑memory stores.
    # ------------------------------------------------------------
    elif mode == MemoryMode.TEST:
        kv_store = RedisKeyValueStore(testing=True)
        vector_store = InMemoryVectorStore()
        graph_store = NetworkXGraphStore()
        # Event-publishing not relevant in test mode; default to False to avoid accidental Kafka use.
        eventing_enabled = False

    # ------------------------------------------------------------
    # Evented enterprise / cloud managed – production configuration.
    # ------------------------------------------------------------
    elif mode in (MemoryMode.EVENTED_ENTERPRISE, MemoryMode.CLOUD_MANAGED):
        # Evented enterprise / cloud managed – production configuration.
        redis_cfg = config.get("redis", {})
        qdrant_config = config.get("qdrant", {})

        # Ensure path is not passed if other connection details are present for Qdrant
        if "url" in qdrant_config or "host" in qdrant_config or "location" in qdrant_config:
            qdrant_config.pop("path", None)

        # Use Redis for KV store (as per tests) – real client if host/port provided, else testing fake.
        # Determine if a Postgres URL is supplied – if so, build a hybrid store (Postgres primary, Redis cache).
        postgres_cfg = config.get("postgres", {})
        if postgres_cfg.get("url"):
            # Create concrete Postgres and Redis stores.
            pg_store = PostgresKeyValueStore(url=postgres_cfg["url"])
            redis_store = (
                RedisKeyValueStore(**redis_cfg) if redis_cfg else RedisKeyValueStore(testing=True)
            )
            kv_store = PostgresRedisHybridStore(pg_store=pg_store, redis_store=redis_store)
        else:
            # No Postgres configured – fall back to Redis only (or a testing fake).
            kv_store = (
                RedisKeyValueStore(**redis_cfg) if redis_cfg else RedisKeyValueStore(testing=True)
            )
        vector_store = QdrantVectorStore(collection_name=namespace, **qdrant_config)
        graph_store = NetworkXGraphStore()
        # Event-publishing flag for production
        eventing_enabled = config.get("eventing", {}).get("enabled", True)

    else:
        raise ValueError(f"Unsupported memory mode: {mode}")

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
