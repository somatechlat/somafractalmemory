"""Thin async Redis cache wrapper used across Soma services."""

from __future__ import annotations

import logging
from typing import Any

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - redis optional in some environments
    Redis = None  # type: ignore

LOGGER = logging.getLogger(__name__)


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

    async def get(self, key: str) -> Any | None:
        value = await self._client.get(key)
        return value

    async def set(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        await self._client.set(key, value, ex=ttl or self._default_ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def close(self) -> None:
        await self._client.close()


__all__ = ["RedisCache"]
