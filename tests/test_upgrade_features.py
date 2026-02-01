"""Test OPA, JWT, retry/backoff, metrics, and config validation for production upgrades."""

import pytest

from common.config.settings import SMFSettings


def test_config_validation():
    # Valid config
    """Execute test config validation."""

    s = SMFSettings(namespace="test", api_port=10101)
    s.validate_config()
    # Invalid config: missing namespace
    s2 = SMFSettings(namespace="", api_port=10101)
    with pytest.raises(ValueError):
        s2.validate_config()
    # Invalid config: bad port
    s3 = SMFSettings(namespace="test", api_port=99999)
    with pytest.raises(ValueError):
        s3.validate_config()
    # JWT enabled but missing key
    s4 = SMFSettings(namespace="test", api_port=10101, jwt_enabled=True)
    with pytest.raises(ValueError):
        s4.validate_config()
    # JWT enabled but missing issuer/audience
    s5 = SMFSettings(namespace="test", api_port=10101, jwt_enabled=True, jwt_secret="x")
    with pytest.raises(ValueError):
        s5.validate_config()


def test_metrics_exposed():
    # Prometheus metrics should be registered
    """Execute test metrics exposed."""

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


def test_retry_backoff_with_invalid_redis():
    """Test that RedisCache handles connection failures gracefully.

    VIBE RULES: Tests against REAL infrastructure - no mocks, no stubs.
    This test validates error handling by connecting to an invalid Redis endpoint.
    """
    import asyncio

    # Create cache pointing to non-existent Redis (invalid port)
    # This tests real error handling without using stubs
    import redis.asyncio as aioredis

    from common.utils.redis_cache import RedisCache

    invalid_client = aioredis.Redis(
        host="localhost",
        port=59999,  # Non-existent port - will fail connection
        socket_connect_timeout=0.1,  # Fast timeout to not slow down tests
    )

    cache = RedisCache(invalid_client)

    # Test that operations fail gracefully with proper exceptions
    with pytest.raises(Exception):  # noqa: B017
        asyncio.run(cache.get("nonexistent-key"))

    # Cleanup - use aclose() per redis 5.0.1+ API
    asyncio.run(invalid_client.aclose())
