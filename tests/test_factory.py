from unittest.mock import MagicMock, patch

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system
from somafractalmemory.implementations.storage import (
    InMemoryVectorStore,
    QdrantVectorStore,
    RedisKeyValueStore,
)


def test_create_on_demand_mode():
    memory = create_memory_system(MemoryMode.TEST, "test_on_demand")
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert not hasattr(memory, "prediction_provider")
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    assert memory.kv_store.client.__class__.__name__ == "FakeRedis"
    # Default now uses in-memory vector store; can be forced to Qdrant via config
    assert isinstance(memory.vector_store, InMemoryVectorStore)


def test_create_local_agent_mode(tmp_path):
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},  # Use fakeredis for local agent test
    }
    memory = create_memory_system(MemoryMode.DEVELOPMENT, "test_local_agent", config=config)
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert not hasattr(memory, "prediction_provider")
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    assert memory.kv_store.client.__class__.__name__ == "FakeRedis"
    assert isinstance(memory.vector_store, QdrantVectorStore)
    assert memory.vector_store.is_on_disk is True


def test_create_enterprise_mode(tmp_path):
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},  # Use fakeredis for enterprise test
    }
    memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "test_enterprise", config=config)
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert not hasattr(memory, "prediction_provider")
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    assert memory.kv_store.client.__class__.__name__ == "FakeRedis"


@patch("redis.Redis", new_callable=MagicMock)
@patch("qdrant_client.QdrantClient", new_callable=MagicMock)
def test_create_enterprise_mode_real_connections(mock_qdrant, mock_redis):
    """Tests that the factory correctly configures for a real enterprise setup."""
    config = {
        "redis": {"host": "remote-redis", "port": 6379},
        "qdrant": {"url": "http://remote-qdrant:6333"},
    }
    create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "test_enterprise_real", config=config)

    # Assert that the Redis client was called with the correct host and port
    mock_redis.assert_called_with(host="remote-redis", port=6379, db=0)

    # Assert that the Qdrant client was called with the correct URL
    mock_qdrant.assert_called_with(url="http://remote-qdrant:6333")
