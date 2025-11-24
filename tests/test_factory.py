# No mock imports needed – tests now use real Redis and Qdrant services.

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system
from somafractalmemory.implementations.storage import (
    QdrantVectorStore,
    RedisKeyValueStore,
)


def test_create_evented_in_memory():
    # Force the factory to use the real Qdrant vector store (no in‑memory fallback).
    memory = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE,
        "test_on_demand",
        config={"redis": {"host": "localhost", "port": 40022}},
    )
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert not hasattr(memory, "prediction_provider")
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    # With the real Redis service the client should be an actual ``redis.Redis`` instance.
    from redis import Redis as RealRedis

    assert isinstance(memory.kv_store.client, RealRedis)
    # The vector store must now be a real Qdrant instance.
    from somafractalmemory.implementations.storage import QdrantVectorStore

    assert isinstance(memory.vector_store, QdrantVectorStore)


def test_create_evented_with_disk_qdrant(tmp_path):
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"host": "localhost", "port": 40022},  # Real Redis instance
    }
    memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "test_local_agent", config=config)
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert not hasattr(memory, "prediction_provider")
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    from redis import Redis as RealRedis

    assert isinstance(memory.kv_store.client, RealRedis)
    assert isinstance(memory.vector_store, QdrantVectorStore)
    assert memory.vector_store.is_on_disk is True


def test_create_enterprise_mode(tmp_path):
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"host": "localhost", "port": 40022},  # Real Redis instance
    }
    memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "test_enterprise", config=config)
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert not hasattr(memory, "prediction_provider")
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    from redis import Redis as RealRedis

    assert isinstance(memory.kv_store.client, RealRedis)


def test_create_enterprise_mode_real_connections():
    """Validate that the factory builds a memory system using real Redis and Qdrant.

    Instead of mocking the external clients, we instantiate the system with a
    concrete configuration that points at the services provided by the Docker
    compose stack (Redis on ``localhost:40022`` and Qdrant on ``localhost:40023``).
    The test then checks that the resulting objects are the expected concrete
    implementations.
    """
    config = {
        "redis": {"host": "localhost", "port": 40022},
        "qdrant": {"url": "http://localhost:40023"},
    }
    memory = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE, "test_enterprise_real", config=config
    )

    # The KV store should be a real Redis client wrapper, not the Fakeredis shim.
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    # Its underlying client must be an actual ``redis.Redis`` instance.
    from redis import Redis as RealRedis

    assert isinstance(memory.kv_store.client, RealRedis)

    # The vector store should be a Qdrant client implementation.
    from somafractalmemory.implementations.storage import QdrantVectorStore

    assert isinstance(memory.vector_store, QdrantVectorStore)
