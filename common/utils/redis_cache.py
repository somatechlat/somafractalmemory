"""Thin async Redis cache wrapper used across Soma services."""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter

# ``tenacity`` provides robust retry decorators, but it is an optional
# dependency. The test suite only exercises the cache in a limited way, so we
# fall back to a no‑op ``retry`` decorator when the library is unavailable.
try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except Exception:  # pragma: no cover - tenacity not installed

    def retry(*_args, **_kwargs):  # type: ignore
        """Fallback decorator that returns the original function unchanged.

        This mimics the ``tenacity.retry`` signature sufficiently for the
        ``@retry`` usages below, allowing the module to be imported without the
        external package.
        """

        def decorator(func):
            """Execute decorator.

            Args:
                func: The func.
            """

            return func

        return decorator

    # Provide fallback implementations for the retry configuration objects
    # used as arguments; they are not needed when the decorator is a no-op.
    def stop_after_attempt(_):  # pragma: no cover
        """Execute stop after attempt.

        Args:
            _: The _.
        """

        return None

    def wait_exponential(*_, **__):  # pragma: no cover
        """Execute wait exponential."""

        return None


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
        """Initialize the instance."""

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
        """Execute from url.

        Args:
            url: The url.
        """

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
        """Execute get.

        Args:
            key: The key.
        """

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
        """Execute set.

        Args:
            key: The key.
            value: The value.
        """

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
        """Execute delete.

        Args:
            key: The key.
        """

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
        """Execute close."""

        REDIS_OPS.labels(method="close").inc()
        try:
            await self._client.close()
        except Exception as e:
            REDIS_ERRORS.labels(method="close").inc()
            print(f"[RedisCache] close() failed: {e}")
            raise


__all__ = ["RedisCache"]
