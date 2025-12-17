"""
Redis Key-Value Store implementation for SomaFractalMemory.

This module provides Redis-backed implementations of the IKeyValueStore
interface, including a hybrid Postgres+Redis store for production use.
"""

import inspect
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager
from typing import Optional

import redis
from redis.exceptions import ConnectionError

from somafractalmemory.interfaces.storage import IKeyValueStore

# Module-level cache for shared connection pools to enable connection
# pooling and client reuse across multiple store instances.
_redis_connection_pools: dict[tuple[str, int, int], redis.ConnectionPool] = {}


class RedisKeyValueStore(IKeyValueStore):
    """Redis implementation of the key-value store interface.

    All testing-related branches and in-process fallbacks have been removed per
    the Vibe Coding Rules. The store now always operates against a real Redis
    instance created via a shared connection pool.
    """

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        # Create (or reuse) a connection pool for the given host/port/db.
        pool_key = (str(host), int(port), int(db))
        pool = _redis_connection_pools.get(pool_key)
        if pool is None:
            pool = redis.ConnectionPool(host=host, port=port, db=db)
            _redis_connection_pools[pool_key] = pool
        self.client = redis.Redis(connection_pool=pool)

    def lock(self, name: str, timeout: int = 10) -> AbstractContextManager:
        """Acquire a distributed lock."""
        return self.client.lock(name, timeout=timeout)

    def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            return bool(self.client.ping())
        except ConnectionError:
            return False

    def set(self, key: str, value: bytes):
        """Store a key-value pair."""
        self.client.set(key, value)

    def get(self, key: str) -> bytes | None:
        """Retrieve a value by key."""
        result = self.client.get(key)
        if inspect.isawaitable(result):
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(result)
        if isinstance(result, bytes | type(None)):
            return result
        return None

    def delete(self, key: str):
        """Delete a key-value pair."""
        self.client.delete(key)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        """Iterate over keys matching a pattern."""
        for key in self.client.scan_iter(pattern):
            if isinstance(key, bytes | bytearray):
                yield key.decode("utf-8")
            else:
                yield str(key)

    def hgetall(self, key: str) -> dict[bytes, bytes]:
        """Get all fields and values in a hash."""
        result = self.client.hgetall(key)
        if inspect.isawaitable(result):
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(result)
        if isinstance(result, dict):
            return {
                k: v for k, v in result.items() if isinstance(k, bytes) and isinstance(v, bytes)
            }
        return {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        """Set multiple hash fields."""
        self.client.hset(key, mapping=dict(mapping))


class PostgresRedisHybridStore(IKeyValueStore):
    """Combine a PostgresKeyValueStore (canonical) with a RedisKeyValueStore.

    * ``set`` writes to both stores.
    * ``get`` tries Redis first (cache hit) and falls back to Postgres.
    * ``delete`` removes from both.
    * ``scan_iter`` merges keys from both stores, deduplicating.
    * ``hgetall`` / ``hset`` prefer Postgres, but also keep Redis in sync.
    * ``lock`` uses Redis if available, otherwise falls back to Postgres lock.
    * ``health_check`` requires both backends to be healthy.
    """

    def __init__(
        self, pg_store: "IKeyValueStore", redis_store: Optional["RedisKeyValueStore"] = None
    ):
        self.pg_store = pg_store
        self.redis_store = redis_store

    def set(self, key: str, value: bytes):
        """Write to both stores."""
        self.pg_store.set(key, value)
        if self.redis_store:
            self.redis_store.set(key, value)

    def get(self, key: str) -> bytes | None:
        """Try Redis first, fall back to Postgres."""
        if self.redis_store:
            cached = self.redis_store.get(key)
            if cached is not None:
                return cached
        return self.pg_store.get(key)

    def delete(self, key: str):
        """Delete from both stores."""
        self.pg_store.delete(key)
        if self.redis_store:
            self.redis_store.delete(key)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        """Merge keys from both stores, deduplicating."""
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
        """Get hash from Postgres, fall back to Redis."""
        pg_val = self.pg_store.hgetall(key)
        if pg_val:
            return pg_val
        if self.redis_store:
            return self.redis_store.hgetall(key)
        return {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        """Set hash in both stores."""
        self.pg_store.hset(key, mapping)
        if self.redis_store:
            self.redis_store.hset(key, mapping)

    def lock(self, name: str, timeout: int = 10) -> AbstractContextManager:
        """Use Redis lock if available, otherwise Postgres."""
        if self.redis_store:
            return self.redis_store.lock(name, timeout)
        return self.pg_store.lock(name, timeout)

    def health_check(self) -> bool:
        """Check both backends are healthy."""
        ok = self.pg_store.health_check()
        if self.redis_store:
            ok = ok and self.redis_store.health_check()
        return ok
