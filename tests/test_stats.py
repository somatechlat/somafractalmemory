import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},
    }
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "stats_ns", config=config)


def test_memory_stats_counts(mem: SomaFractalMemoryEnterprise):
    """Test basic memory statistics counting."""
    # Initially empty
    assert mem.memory_stats()["total_memories"] == 0

    # Store different types of memories
    c1, c2, c3 = (1, 1, 1), (2, 2, 2), (3, 3, 3)
    mem.store_memory(c1, {"content": "episodic memory 1"}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c2, {"content": "episodic memory 2"}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c3, {"content": "semantic memory"}, memory_type=MemoryType.SEMANTIC)

    # Verify counts
    stats = mem.memory_stats()
    assert stats["total_memories"] >= 3
    assert stats["episodic"] >= 2
    assert stats["semantic"] >= 1
