import pytest

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    # Use real Redis service (provided by Docker compose) and on‑disk Qdrant.
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"host": "redis", "port": 6379},
    }
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "additional_ns", config=config)


def test_delete_removes_memory(mem: SomaFractalMemoryEnterprise):
    """Test that delete operation properly removes stored memory."""
    coord = (9, 9, 9)
    mem.store_memory(coord, {"data": "test_value"})
    assert mem.retrieve(coord) is not None
    mem.delete(coord)
    assert mem.retrieve(coord) is None


def test_basic_memory_persistence(mem: SomaFractalMemoryEnterprise):
    """Test basic memory storage and retrieval persistence."""
    coord = (7, 7, 7)
    payload = {"content": "test data", "importance": 0.5}
    mem.store_memory(coord, payload)
    retrieved = mem.retrieve(coord)
    assert retrieved is not None
    assert retrieved["content"] == "test data"
    assert retrieved["importance"] == 0.5
