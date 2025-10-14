"""Async storage implementations for SomaFractalMemory.

These provide real async clients for Redis and Postgres using
`redis.asyncio` and `asyncpg`. They intentionally raise a clear error if the
required packages are not installed so deployments must use real servers and
real credentials (no mocks or bypasses).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover - runtime dep
    aioredis = None  # type: ignore

try:
    import asyncpg
except Exception:  # pragma: no cover - runtime dep
    asyncpg = None  # type: ignore

from common.utils.logger import get_logger

LOGGER = get_logger("somafractalmemory").bind(component="async_storage")


class AsyncRedisKeyValueStore:
    def __init__(self, client: aioredis.Redis) -> None:
        if aioredis is None:
            raise RuntimeError("redis[asyncio] must be installed to use AsyncRedisKeyValueStore")
        self.client = client

    @classmethod
    def from_url(cls, url: str, **kwargs) -> AsyncRedisKeyValueStore:
        if aioredis is None:
            raise RuntimeError("redis[asyncio] must be installed to use AsyncRedisKeyValueStore")
        client = aioredis.from_url(url, **kwargs)
        return cls(client)

    async def set(self, key: str, value: bytes) -> None:
        await self.client.set(key, value)

    async def get(self, key: str) -> bytes | None:
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def scan_iter(self, pattern: str) -> AsyncIterator[str]:
        async for k in self.client.scan_iter(match=pattern):
            if isinstance(k, (bytes | bytearray)):
                yield k.decode("utf-8")
            else:
                yield str(k)

    async def hgetall(self, key: str) -> dict[bytes, bytes]:
        res = await self.client.hgetall(key)
        # normalize only byte-like keys/values into bytes; keep other types as-is
        return {k: v for k, v in res.items() if isinstance(k, (bytes | bytearray))}

    async def hset(self, key: str, mapping: dict[bytes, bytes]) -> None:
        await self.client.hset(key, mapping=mapping)

    async def lock(self, name: str, timeout: int = 10):
        return self.client.lock(name, timeout=timeout)

    async def close(self) -> None:
        try:
            await self.client.close()
        except Exception:
            pass

    async def health_check(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception:
            return False


class AsyncPostgresKeyValueStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        if asyncpg is None:
            raise RuntimeError("asyncpg must be installed to use AsyncPostgresKeyValueStore")
        self._pool = pool

    @classmethod
    async def from_url(cls, dsn: str, **kwargs) -> AsyncPostgresKeyValueStore:
        if asyncpg is None:
            raise RuntimeError("asyncpg must be installed to use AsyncPostgresKeyValueStore")
        pool = await asyncpg.create_pool(dsn, **kwargs)
        return cls(pool)

    async def set(self, key: str, value: bytes) -> None:
        async with self._pool.acquire() as conn:
            # normalize value to a JSON string for storage
            if isinstance(value, (bytes | bytearray)):
                val_to_store = value.decode("utf-8")
            elif isinstance(value, dict):
                val_to_store = json.dumps(value)
            else:
                val_to_store = str(value)
            await conn.execute(
                "INSERT INTO kv_store(key, value) VALUES($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2",
                key,
                val_to_store,
            )

    async def get(self, key: str) -> bytes | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM kv_store WHERE key = $1", key)
            if row:
                return json.dumps(row["value"]).encode("utf-8")
            return None

    async def delete(self, key: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM kv_store WHERE key = $1", key)

    async def scan_iter(self, pattern: str) -> AsyncIterator[str]:
        like = pattern.replace("*", "%")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                async for rec in conn.cursor("SELECT key FROM kv_store WHERE key LIKE $1", like):
                    yield rec["key"]

    async def hgetall(self, key: str) -> dict[bytes, bytes]:
        v = await self.get(key)
        if not v:
            return {}
        try:
            data = json.loads(v)
            return {k.encode("utf-8"): json.dumps(val).encode("utf-8") for k, val in data.items()}
        except Exception:
            return {}

    async def hset(self, key: str, mapping: dict[bytes, bytes]) -> None:
        obj = {
            k.decode("utf-8"): json.loads(v) if isinstance(v, (bytes | bytearray)) else v
            for k, v in mapping.items()
        }
        await self.set(key, json.dumps(obj).encode("utf-8"))

    async def lock(self, name: str, timeout: int = 10):
        return None

    async def close(self) -> None:
        await self._pool.close()

    async def health_check(self) -> bool:
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            LOGGER.error("Postgres health_check failed", error=str(e))
            return False


__all__ = ["AsyncRedisKeyValueStore", "AsyncPostgresKeyValueStore"]
