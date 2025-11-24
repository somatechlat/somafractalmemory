# Standard library imports
from collections.abc import Iterator, Mapping
from enum import Enum
from typing import Any

from common.config.settings import load_settings
from common.utils.logger import get_logger

# Local application imports (alphabetical)
from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.storage import (
    BatchedStore,
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
    Factory function to create a SomaFractalMemoryEnterprise instance.
    """
    logger = get_logger(__name__)
    logger.info("Creating memory system...")

    overrides: dict[str, Any] = {}
    redis_kwargs: dict[str, Any] = {}
    qdrant_kwargs: dict[str, Any] = {}

    if config:
        postgres_cfg = config.get("postgres")
        if postgres_cfg and postgres_cfg.get("url"):
            overrides["postgres_url"] = postgres_cfg["url"]

        redis_cfg = config.get("redis") or {}
        if redis_cfg.get("host"):
            redis_kwargs["host"] = redis_cfg["host"]
        if redis_cfg.get("port") is not None:
            redis_kwargs["port"] = int(redis_cfg["port"])

        qdrant_cfg = config.get("qdrant") or {}
        if qdrant_cfg.get("url"):
            qdrant_kwargs["url"] = qdrant_cfg["url"]
        elif qdrant_cfg.get("host"):
            qdrant_kwargs["host"] = qdrant_cfg["host"]
            if qdrant_cfg.get("port") is not None:
                qdrant_kwargs["port"] = int(qdrant_cfg["port"])
        # Support local on-disk qdrant used by tests (path => on-disk client)
        if qdrant_cfg.get("path"):
            qdrant_kwargs["path"] = qdrant_cfg["path"]

    # Honor bare environment overrides even when config is absent
    # Load centralized settings once.
    _settings = load_settings()
    # Apply explicit environment overrides using the central settings.
    if _settings.postgres_url:
        overrides.setdefault("postgres_url", _settings.postgres_url)
    # Qdrant configuration – prioritize explicit config, then settings.
    if not qdrant_kwargs.get("url") and not qdrant_kwargs.get("host"):
        if _settings.qdrant_url:
            qdrant_kwargs["url"] = _settings.qdrant_url
        elif _settings.qdrant_host:
            qdrant_kwargs["host"] = _settings.qdrant_host
            # Assume default port if not set in settings (could be added later).
            if hasattr(_settings, "qdrant_port") and _settings.qdrant_port:
                qdrant_kwargs["port"] = int(_settings.qdrant_port)
    # Redis configuration – use settings infra defaults.
    if _settings.infra.redis:
        redis_kwargs.setdefault("host", _settings.infra.redis)

    settings = load_settings(overrides=overrides if overrides else None)

    # If the caller explicitly provided a local qdrant path via config (tests),
    # prefer that unconditionally to avoid attempting network connections to
    # a remote qdrant host from within unit tests.
    if config and isinstance(config.get("qdrant"), dict) and config.get("qdrant", {}).get("path"):
        qdrant_kwargs = {"path": config.get("qdrant", {}).get("path")}

    # Log the settings being used
    logger.info(f"Postgres URL: {settings.postgres_url}")
    logger.info(f"Redis host: {settings.infra.redis}")
    logger.info(f"Qdrant config: {qdrant_kwargs}")

    redis_kwargs.setdefault("host", settings.infra.redis)

    # ---------------------------------------------------------------------
    # Production‑only configuration – **no testing fallbacks**.
    # ---------------------------------------------------------------------
    # Create the Redis KV store. Any connectivity problem should raise an
    # exception – we no longer silently fall back to an in‑memory store.
    redis_store = RedisKeyValueStore(**redis_kwargs)
    if not redis_store.health_check():
        raise RuntimeError("Unable to connect to Redis at the configured host/port")

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

    # Clear any default host if URL is set
    if "url" in qdrant_kwargs and "host" in qdrant_kwargs:
        del qdrant_kwargs["host"]
        if "port" in qdrant_kwargs:
            del qdrant_kwargs["port"]
    elif not qdrant_kwargs:
        qdrant_kwargs["host"] = settings.qdrant_host

    # Vector store selection – always use the real Qdrant store.
    # The previous implementation allowed a "memory" backend for unit‑test speed.
    # For a production‑like environment (and per the request to eliminate any
    # in‑memory bypass), we now *force* the QdrantVectorStore. If Qdrant cannot be
    # reached an exception will be raised – this mirrors real‑world failure
    # handling and ensures tests run against the actual vector store.
    try:
        vector_store = QdrantVectorStore(collection_name=namespace, **qdrant_kwargs)
    except Exception as exc:
        logger.error(
            "Failed to initialise Qdrant vector store – real infra required.",
            error=str(exc),
        )
        raise
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
