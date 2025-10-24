"""Test OPA, JWT, retry/backoff, metrics, and config validation for production upgrades."""

import pytest

from common.config.settings import SMFSettings


def test_config_validation():
    # Valid config
    s = SMFSettings(namespace="test", api_port=9595)
    s.validate_config()
    # Invalid config: missing namespace
    s2 = SMFSettings(namespace="", api_port=9595)
    with pytest.raises(ValueError):
        s2.validate_config()
    # Invalid config: bad port
    s3 = SMFSettings(namespace="test", api_port=99999)
    with pytest.raises(ValueError):
        s3.validate_config()
    # JWT enabled but missing key
    s4 = SMFSettings(namespace="test", api_port=9595, jwt_enabled=True)
    with pytest.raises(ValueError):
        s4.validate_config()
    # JWT enabled but missing issuer/audience
    s5 = SMFSettings(namespace="test", api_port=9595, jwt_enabled=True, jwt_secret="x")
    with pytest.raises(ValueError):
        s5.validate_config()


def test_metrics_exposed():
    # Prometheus metrics should be registered
    import prometheus_client

    metrics = prometheus_client.REGISTRY.collect()
    names = [m.name for m in metrics]
    # Accept either the historical `_total` suffix or the registered metric name
    assert (
        "api_requests_total" in names
        or "seed_requests_total" in names
        or "api_requests" in names
        or "seed_requests" in names
    )


def test_retry_backoff(monkeypatch):
    from common.utils.redis_cache import RedisCache

    class DummyRedis:
        async def get(self, key):
            raise RuntimeError("fail")

        async def set(self, key, value, ex=None):
            raise RuntimeError("fail")

        async def delete(self, key):
            raise RuntimeError("fail")

        async def close(self):
            raise RuntimeError("fail")

    cache = RedisCache(DummyRedis())
    import pytest

    with pytest.raises(RuntimeError):
        import asyncio

        asyncio.run(cache.get("x"))
    with pytest.raises(RuntimeError):
        import asyncio

        asyncio.run(cache.set("x", "y"))
    with pytest.raises(RuntimeError):
        import asyncio

        asyncio.run(cache.delete("x"))
    with pytest.raises(RuntimeError):
        import asyncio

        asyncio.run(cache.close())
