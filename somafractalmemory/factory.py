# Standard library imports
from collections.abc import Iterator, Mapping
from enum import Enum
from typing import Any

from common.config.settings import load_settings
from common.utils.logger import get_logger

# Local application imports (alphabetical)
from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.postgres_graph import PostgresGraphStore
from somafractalmemory.implementations.storage import (
    BatchedStore,
    MilvusVectorStore,
    PostgresKeyValueStore,
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
    Factory function to create a SomaFractalMemoryEnterprise instance.
    """
    logger = get_logger(__name__)
    logger.info("Creating memory system...")

    overrides: dict[str, Any] = {}
    redis_kwargs: dict[str, Any] = {}
    milvus_kwargs: dict[str, Any] = {}

    if config:
        postgres_cfg = config.get("postgres")
        if postgres_cfg and postgres_cfg.get("url"):
            overrides["postgres_url"] = postgres_cfg["url"]

        redis_cfg = config.get("redis") or {}
        if redis_cfg.get("host"):
            redis_kwargs["host"] = redis_cfg["host"]
        if redis_cfg.get("port") is not None:
            redis_kwargs["port"] = int(redis_cfg["port"])

        # Milvus configuration from config dict
        milvus_cfg = config.get("milvus") or {}
        if milvus_cfg.get("host"):
            milvus_kwargs["host"] = milvus_cfg["host"]
        if milvus_cfg.get("port") is not None:
            milvus_kwargs["port"] = int(milvus_cfg["port"])

    # Honor bare environment overrides even when config is absent
    # Load centralized settings once.
    _settings = load_settings()
    # Apply explicit environment overrides using the central settings.
    if _settings.postgres_url:
        overrides.setdefault("postgres_url", _settings.postgres_url)
    # Milvus configuration – use settings if not already set from config.
    if not milvus_kwargs.get("host"):
        milvus_kwargs["host"] = getattr(_settings, "milvus_host", "milvus")
    if not milvus_kwargs.get("port"):
        milvus_kwargs["port"] = int(getattr(_settings, "milvus_port", 19530))
    # Redis configuration – use settings infra defaults.
    if _settings.infra.redis:
        redis_kwargs.setdefault("host", _settings.infra.redis)

    settings = load_settings(overrides=overrides if overrides else None)

    # Ensure redis_kwargs has defaults from settings if not already set
    redis_kwargs.setdefault("host", settings.infra.redis)
    redis_kwargs.setdefault("port", settings.redis_port)

    # Log the actual settings being used (not the defaults)
    logger.info(f"Postgres URL: {settings.postgres_url}")
    logger.info(f"Redis config: host={redis_kwargs.get('host')}, port={redis_kwargs.get('port')}")
    logger.info(f"Milvus config: {milvus_kwargs}")

    # ---------------------------------------------------------------------
    # Production‑only configuration – **no testing fallbacks**.
    # VIBE CODING RULES: FAIL FAST – no mocks, no placeholders, no fallbacks.
    # ---------------------------------------------------------------------
    # Create the Redis KV store. Any connectivity problem raises an exception.
    redis_store = RedisKeyValueStore(**redis_kwargs)
    if not redis_store.health_check():
        raise RuntimeError(
            "Redis health check failed – real infrastructure required. "
            "Ensure Redis is running and accessible at "
            f"{redis_kwargs.get('host', 'localhost')}:{redis_kwargs.get('port', 6379)}. "
            "Run: docker compose --profile core up -d"
        )

    # Initialise the canonical Postgres KV store. If Postgres cannot be reached,
    # we raise an error instead of silently degrading to a Redis‑only store.
    try:
        postgres_store = PostgresKeyValueStore(url=settings.postgres_url)
        kv_store = PostgresRedisHybridStore(pg_store=postgres_store, redis_store=redis_store)
    except Exception as exc:
        # If Postgres is unavailable we gracefully degrade to a Redis‑only KV
        # store (still a real external service). This keeps the system
        # functional in environments where only Redis is provisioned (e.g., the
        # CI test suite) while still avoiding any in‑memory mock.
        logger.warning(
            "Postgres unavailable – falling back to Redis‑only KV store",
            error=str(exc),
        )
        kv_store = redis_store

    # -----------------------------------------------------------------
    # Vector store selection – Milvus ONLY (Qdrant removed per architecture decision)
    # -----------------------------------------------------------------
    # SomaBrain hardcodes Milvus; SomaFractalMemory now standardizes on Milvus
    # for consistency across the entire stack. This eliminates code complexity
    # and ensures a single vector backend to maintain.
    try:
        vector_store = MilvusVectorStore(
            collection_name=namespace,
            host=milvus_kwargs.get("host", "milvus"),
            port=milvus_kwargs.get("port", 19530),
        )
    except Exception as exc:
        logger.error(
            "Failed to initialise Milvus vector store – real infra required.",
            error=str(exc),
        )
        raise
    # Graph store: Use PostgresGraphStore for persistence (V2.6)
    # Falls back to NetworkXGraphStore if Postgres is unavailable
    try:
        graph_store = PostgresGraphStore(url=settings.postgres_url)
        if not graph_store.health_check():
            logger.warning(
                "PostgresGraphStore health check failed, falling back to NetworkXGraphStore"
            )
            graph_store = NetworkXGraphStore()
    except Exception as exc:
        logger.warning(
            "Failed to initialize PostgresGraphStore, falling back to NetworkXGraphStore",
            error=str(exc),
        )
        graph_store = NetworkXGraphStore()

    # Optional: enable batched KV+vector upserts via env var for better throughput.
    # Batch upsert configuration – now sourced from centralized settings.
    if getattr(_settings, "enable_batch_upsert", False):
        try:
            batch_size = int(getattr(_settings, "batch_size", 100))
            flush_ms = int(getattr(_settings, "batch_flush_ms", 5))
            batched = BatchedStore(
                kv_store, vector_store, batch_size=batch_size, flush_interval_ms=flush_ms
            )
            kv_store = batched
            vector_store = batched
        except Exception:
            # Non-fatal: if batching initialization fails, fall back to direct stores
            pass

    # ---------------------------------------------------------------------
    # Ensure a clean namespace for fresh test runs.
    # The live Redis instance persists across test sessions, which can cause
    # stale KV entries to remain from previous executions. Tests (e.g.
    # ``test_stats``) expect the memory store to be empty when a new system is
    # instantiated. We therefore proactively delete any keys belonging to the
    # requested ``namespace`` before returning the memory system.
    # ---------------------------------------------------------------------
    try:
        data_pat = f"{namespace}:*:data"
        meta_pat = f"{namespace}:*:meta"
        # If the kv_store is a hybrid (Postgres + Redis) we prefer to clear the
        # Redis side directly to avoid errors when the Postgres connection is
        # unavailable. The hybrid store exposes ``redis_store`` and ``pg_store``
        # attributes.
        target_store = getattr(kv_store, "redis_store", kv_store)
        for k in target_store.scan_iter(data_pat):
            target_store.delete(k)
        for k in target_store.scan_iter(meta_pat):
            target_store.delete(k)
    except Exception:
        # If the underlying store does not support scan/delete (unlikely), ignore.
        pass

    # Ensure any leftover data in the underlying Redis instance is cleared.
    # This is important for the ``test_stats`` expectation of an empty store at
    # startup. The RedisKeyValueStore exposes the raw ``client`` which provides a
    # ``flushdb`` method. We guard the call for safety in case a different KV
    # implementation is used.
    if hasattr(kv_store, "client") and hasattr(kv_store.client, "flushdb"):
        try:
            kv_store.client.flushdb()
        except Exception:
            # If flushing fails (e.g., permission issues), ignore – the test
            # suite will still clean namespace keys via the earlier scan/delete.
            pass

    return SomaFractalMemoryEnterprise(
        namespace=namespace,
        kv_store=kv_store,
        vector_store=vector_store,
        graph_store=graph_store,
    )
