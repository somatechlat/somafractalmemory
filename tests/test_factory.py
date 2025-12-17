# No mock imports needed – tests now use real Redis and Milvus services.
"""
Factory tests for SomaFractalMemory.

These tests verify that the factory correctly creates memory systems
using real infrastructure (Redis, Postgres, Milvus).

VIBE CODING RULES: NO mocks, NO stubs, NO placeholders.
All tests require real infrastructure via docker compose --profile core up -d
"""

import os

import pytest

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system
from somafractalmemory.implementations.storage import (
    MilvusVectorStore,
    RedisKeyValueStore,
)

# Test configuration for localhost connections (tests run on host, not in Docker)
# Structure must match what factory.py expects: nested dicts for redis, postgres, milvus
# Port defaults match docker-compose.yml: Postgres=40021, Redis=40022, Milvus=35003
TEST_CONFIG = {
    "redis": {
        "host": os.environ.get("REDIS_HOST", "localhost"),
        "port": int(os.environ.get("REDIS_PORT", "40022")),
    },
    "postgres": {
        "url": os.environ.get("POSTGRES_URL", "postgresql://soma:soma@localhost:40021/somamemory"),
    },
    "milvus": {
        "host": os.environ.get("MILVUS_HOST", os.environ.get("SOMA_MILVUS_HOST", "localhost")),
        "port": int(os.environ.get("MILVUS_PORT", os.environ.get("SOMA_MILVUS_PORT", "35003"))),
    },
}


@pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Redis, Postgres, Milvus)",
)
def test_create_evented_enterprise():
    """Test factory creates enterprise memory system with real infrastructure."""
    memory = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE,
        "test_factory_enterprise",
        config=TEST_CONFIG,
    )
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert not hasattr(memory, "prediction_provider")
    # KV store should be Redis-backed (or hybrid with Postgres)
    kv = memory.kv_store
    # Check if it's a hybrid store or direct Redis
    if hasattr(kv, "redis_store"):
        assert isinstance(kv.redis_store, RedisKeyValueStore)
    else:
        assert isinstance(kv, RedisKeyValueStore)
    # Vector store must be Milvus (exclusive backend)
    assert isinstance(memory.vector_store, MilvusVectorStore)


@pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Redis, Postgres, Milvus)",
)
def test_create_enterprise_mode_real_connections():
    """Validate that the factory builds a memory system using real Redis and Milvus.

    Instead of mocking the external clients, we instantiate the system with a
    concrete configuration that points at the services provided by the Docker
    compose stack. The test then checks that the resulting objects are the
    expected concrete implementations.
    """
    memory = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE,
        "test_enterprise_real",
        config=TEST_CONFIG,
    )

    # The KV store should be a real Redis client wrapper, not any in-memory shim.
    kv = memory.kv_store
    if hasattr(kv, "redis_store"):
        assert isinstance(kv.redis_store, RedisKeyValueStore)
        from redis import Redis as RealRedis

        assert isinstance(kv.redis_store.client, RealRedis)
    else:
        assert isinstance(kv, RedisKeyValueStore)
        from redis import Redis as RealRedis

        assert isinstance(kv.client, RealRedis)

    # The vector store must be Milvus (exclusive backend per architecture decision)
    assert isinstance(memory.vector_store, MilvusVectorStore)


@pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure",
)
def test_redis_unavailable_raises_runtime_error():
    """Test V1.6: Redis unavailable → factory raises RuntimeError.

    VIBE CODING RULES: No fallback to in-memory stores.
    """
    # Create a config pointing to a non-existent Redis
    config = {
        "redis": {"host": "nonexistent-redis-host-12345", "port": 9999},
    }
    with pytest.raises(RuntimeError, match="Redis health check failed"):
        create_memory_system(
            MemoryMode.EVENTED_ENTERPRISE,
            "test_redis_unavailable",
            config=config,
        )


@pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure",
)
def test_milvus_only_backend():
    """Test V5.5: Milvus is the exclusive vector backend.

    The factory should use MilvusVectorStore and not support any alternatives.
    """
    memory = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE,
        "test_milvus_only",
        config=TEST_CONFIG,
    )
    # Vector store must be Milvus
    assert isinstance(memory.vector_store, MilvusVectorStore)
    # Verify it's not any other type
    assert type(memory.vector_store).__name__ == "MilvusVectorStore"
