"""Thin async Redis cache wrapper used across Soma services."""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter
from tenacity import retry, stop_after_attempt, wait_exponential

REDIS_OPS = Counter("redis_ops_total", "Total Redis cache operations", ["method"])
REDIS_ERRORS = Counter("redis_errors_total", "Redis cache errors", ["method"])
REDIS_RETRIES = Counter("redis_retries_total", "Redis cache retry attempts", ["method"])

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - redis optional in some environments
    Redis = None  # type: ignore


class RedisCache:
    """Helper that encapsulates TTL caching behaviour for Redis."""

    def __init__(self, client: Redis, *, default_ttl: int = 300):
        if Redis is None:
            raise RuntimeError("redis[asyncio] must be installed to use RedisCache")
        self._client = client
        self._default_ttl = default_ttl

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        default_ttl: int = 300,
        encoding: str = "utf-8",
        decode_responses: bool = False,
        **kwargs: Any,
    ) -> RedisCache:
        if Redis is None:
            raise RuntimeError("redis[asyncio] must be installed to use RedisCache")
        client = Redis.from_url(url, encoding=encoding, decode_responses=decode_responses, **kwargs)
        return cls(client, default_ttl=default_ttl)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    async def get(self, key: str) -> Any | None:
        REDIS_OPS.labels(method="get").inc()
        try:
            value = await self._client.get(key)
            return value
        except Exception as e:
            REDIS_ERRORS.labels(method="get").inc()
            print(f"[RedisCache] get({key}) failed: {e}")
            raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    async def set(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        REDIS_OPS.labels(method="set").inc()
        try:
            await self._client.set(key, value, ex=ttl or self._default_ttl)
        except Exception as e:
            REDIS_ERRORS.labels(method="set").inc()
            print(f"[RedisCache] set({key}) failed: {e}")
            raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    async def delete(self, key: str) -> None:
        REDIS_OPS.labels(method="delete").inc()
        try:
            await self._client.delete(key)
        except Exception as e:
            REDIS_ERRORS.labels(method="delete").inc()
            print(f"[RedisCache] delete({key}) failed: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def close(self) -> None:
        REDIS_OPS.labels(method="close").inc()
        try:
            await self._client.close()
        except Exception as e:
            REDIS_ERRORS.labels(method="close").inc()
            print(f"[RedisCache] close() failed: {e}")
            raise


__all__ = ["RedisCache"]
