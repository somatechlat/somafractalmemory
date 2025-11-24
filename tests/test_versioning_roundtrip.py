import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        # Use the real Redis container (host port 40022) instead of the fakeredis shim.
        "redis": {"host": "localhost", "port": 40022},
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
