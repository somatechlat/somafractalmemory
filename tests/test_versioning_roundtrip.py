"""Module test_versioning_roundtrip."""

import os

import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system

# Skip if infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Milvus, Redis, Postgres)",
)


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    """Create memory system using Milvus (Qdrant removed per architecture decision)."""
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    milvus_host = os.environ.get("SOMA_MILVUS_HOST", "localhost")
    milvus_port = int(os.environ.get("SOMA_MILVUS_PORT", 19530))

    config = {
        "redis": {"host": "localhost", "port": redis_port},
        "milvus": {"host": milvus_host, "port": milvus_port},
    }
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "persistence_ns", config=config)


def test_memory_persistence_roundtrip(mem: SomaFractalMemoryEnterprise):
    """Test that stored memories persist correctly and can be retrieved."""
    coord = (1.0, 2.0, 3.0)
    original_data = {"content": "test content", "importance": 0.8}

    # Store memory
    mem.store_memory(coord, original_data, memory_type=MemoryType.EPISODIC)

    # Retrieve and verify
    retrieved = mem.retrieve(coord)
    assert retrieved is not None
    assert retrieved["content"] == "test content"
    assert retrieved["importance"] == 0.8
    assert retrieved["memory_type"] == MemoryType.EPISODIC.value

    # Update memory with new data
    updated_data = {"content": "updated content", "importance": 0.9}
    mem.store_memory(coord, updated_data, memory_type=MemoryType.EPISODIC)

    # Verify update
    retrieved_updated = mem.retrieve(coord)
    assert retrieved_updated is not None
    assert retrieved_updated["content"] == "updated content"
    assert retrieved_updated["importance"] == 0.9
