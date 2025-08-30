import pytest
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.prediction import NoPredictionProvider, OllamaPredictionProvider, ExternalPredictionProvider
from somafractalmemory.implementations.storage import RedisKeyValueStore, QdrantVectorStore, InMemoryVectorStore
from unittest.mock import patch, MagicMock

def test_create_on_demand_mode():
    memory = create_memory_system(MemoryMode.ON_DEMAND, "test_on_demand")
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert isinstance(memory.prediction_provider, NoPredictionProvider)
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    assert memory.kv_store.client.__class__.__name__ == 'FakeRedis'
    # Default now uses in-memory vector store; can be forced to Qdrant via config
    assert isinstance(memory.vector_store, InMemoryVectorStore)

def test_create_local_agent_mode(tmp_path):
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True} # Use fakeredis for local agent test
    }
    memory = create_memory_system(MemoryMode.LOCAL_AGENT, "test_local_agent", config=config)
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert isinstance(memory.prediction_provider, OllamaPredictionProvider)
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    assert memory.kv_store.client.__class__.__name__ == 'FakeRedis'
    assert isinstance(memory.vector_store, QdrantVectorStore)
    assert memory.vector_store.is_on_disk is True


def test_create_enterprise_mode(tmp_path):
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True}, # Use fakeredis for enterprise test
        "external_prediction": {
            "api_key": "test_key",
            "endpoint": "http://test.com"
        }
    }
    memory = create_memory_system(MemoryMode.ENTERPRISE, "test_enterprise", config=config)
    assert isinstance(memory, SomaFractalMemoryEnterprise)
    assert isinstance(memory.prediction_provider, ExternalPredictionProvider)
    assert isinstance(memory.kv_store, RedisKeyValueStore)
    assert memory.kv_store.client.__class__.__name__ == 'FakeRedis'


@patch('redis.Redis', new_callable=MagicMock)
@patch('qdrant_client.QdrantClient', new_callable=MagicMock)
def test_create_enterprise_mode_real_connections(mock_qdrant, mock_redis):
    """Tests that the factory correctly configures for a real enterprise setup."""
    config = {
        "redis": {"host": "remote-redis", "port": 6379},
        "qdrant": {"url": "http://remote-qdrant:6333"}
    }
    create_memory_system(MemoryMode.ENTERPRISE, "test_enterprise_real", config=config)
    
    # Assert that the Redis client was called with the correct host and port
    mock_redis.assert_called_with(host="remote-redis", port=6379, db=0)
    
    # Assert that the Qdrant client was called with the correct URL
    mock_qdrant.assert_called_with(url="http://remote-qdrant:6333")
