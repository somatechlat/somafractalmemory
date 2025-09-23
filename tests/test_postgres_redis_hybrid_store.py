# Integration test for PostgresRedisHybridStore using testcontainers

# Standard library imports
import json
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


@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as postgres:
        time.sleep(2)
        yield postgres


@pytest.fixture(scope="module")
def redis_container():
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
