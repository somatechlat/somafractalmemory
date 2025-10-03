# Integration test for PostgresRedisHybridStore using testcontainers

# Standard library imports
import json
import os
import time

# Third‑party imports
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# Local imports
from somafractalmemory.implementations.storage import (
    PostgresKeyValueStore,
    PostgresRedisHybridStore,
    RedisKeyValueStore,
)

USE_REAL = os.getenv("USE_REAL_INFRA", "0").lower() in ("1", "true", "yes")


@pytest.fixture(scope="module")
def postgres_container():
    if USE_REAL:
        # Use already running compose postgres service
        class _PgDummy:
            def get_connection_url(self):
                return os.getenv(
                    "POSTGRES_URL",
                    "postgresql://postgres:postgres@postgres:5432/somamemory",
                )

        yield _PgDummy()
    else:
        with PostgresContainer("postgres:15-alpine") as postgres:
            time.sleep(2)
            yield postgres


@pytest.fixture(scope="module")
def redis_container():
    if USE_REAL:

        class _RedisDummy:
            def get_container_host_ip(self):
                return os.getenv("REDIS_HOST", "redis")

            def get_exposed_port(self, port):  # noqa: ARG002
                return os.getenv("REDIS_PORT", "6379")

        yield _RedisDummy()
    else:
        with RedisContainer("redis:7-alpine") as redis:
            time.sleep(2)
            yield redis


def test_hybrid_store_set_get(postgres_container, redis_container):
    pg_url = postgres_container.get_connection_url()
    redis_host = redis_container.get_container_host_ip()
    redis_port = int(redis_container.get_exposed_port(6379))

    pg_store = PostgresKeyValueStore(url=pg_url)
    redis_store = RedisKeyValueStore(host=redis_host, port=redis_port)
    hybrid = PostgresRedisHybridStore(pg_store=pg_store, redis_store=redis_store)

    key = "test:key"
    value = json.dumps({"msg": "hello"}).encode("utf-8")

    hybrid.delete(key)
    hybrid.set(key, value)
    # Verify cache hit
    assert redis_store.get(key) == value
    # Simulate cache miss
    redis_store.delete(key)
    assert hybrid.get(key) == value
    # Cleanup
    hybrid.delete(key)
    assert hybrid.get(key) is None


def test_hybrid_store_lock(postgres_container, redis_container):
    pg_url = postgres_container.get_connection_url()
    redis_host = redis_container.get_container_host_ip()
    redis_port = int(redis_container.get_exposed_port(6379))

    pg_store = PostgresKeyValueStore(url=pg_url)
    redis_store = RedisKeyValueStore(host=redis_host, port=redis_port)
    hybrid = PostgresRedisHybridStore(pg_store=pg_store, redis_store=redis_store)

    lock = hybrid.lock("testlock", timeout=5)
    with lock:
        assert True
    with hybrid.lock("testlock", timeout=5):
        assert True
