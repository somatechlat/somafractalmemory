# Standard library imports
from collections.abc import Iterator, Mapping
from enum import Enum
from typing import Any

from common.config.settings import load_settings

# Local application imports (alphabetical)
from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.storage import (
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
    settings = load_settings()

    postgres_store = PostgresKeyValueStore(url=settings.postgres_url)
    redis_store = RedisKeyValueStore(host=settings.infra.redis)

    kv_store = PostgresRedisHybridStore(pg_store=postgres_store, redis_store=redis_store)
    vector_store = QdrantVectorStore(collection_name=namespace, host=settings.qdrant_host)
    graph_store = NetworkXGraphStore()

    return SomaFractalMemoryEnterprise(
        namespace=namespace,
        kv_store=kv_store,
        vector_store=vector_store,
        graph_store=graph_store,
    )
