import pytest

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def memory_manager() -> SomaFractalMemoryEnterprise:
    config = {
        "postgres": {"url": "postgresql://soma:soma@localhost:40001/somamemory"},
        "redis": {"host": "localhost", "port": 40002},
        "qdrant": {"host": "localhost", "port": 40003},
    }
    system = create_memory_system(
        mode=MemoryMode.EVENTED_ENTERPRISE, namespace="test", config=config
    )
    return system


def test_simple_memory_save_recall(memory_manager: SomaFractalMemoryEnterprise):
    # Create a memory with test content
    memory_data = {
        "content": "This is a test memory from 2025",
        "timestamp": "2025-10-15T12:00:00Z",
        "type": "test",
    }
    coordinate = (1.0, 2.0)  # Simple test coordinate

    # Store the memory
    memory_manager.store(coordinate=coordinate, value=memory_data)

    # Retrieve the memory using the same coordinate
    recalled = memory_manager.retrieve(coordinate)

    # Verify the recalled content matches what we stored
    assert recalled is not None, "Memory should be retrievable"
    assert recalled["content"] == memory_data["content"], "Content should match"
    assert recalled["timestamp"] == memory_data["timestamp"], "Timestamp should be preserved"
    assert recalled["type"] == memory_data["type"], "Type should be preserved"
