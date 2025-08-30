import pytest
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import SomaFractalMemoryEnterprise, MemoryType


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},
    }
    return create_memory_system(MemoryMode.LOCAL_AGENT, "stats_ns", config=config)


def test_memory_stats_counts(mem: SomaFractalMemoryEnterprise):
    assert mem.memory_stats()["total_memories"] == 0
    c1, c2, c3 = (1,1,1), (2,2,2), (3,3,3)
    mem.store_memory(c1, {"d": 1}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c2, {"d": 2}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c3, {"f": 3}, memory_type=MemoryType.SEMANTIC)
    stats = mem.memory_stats()
    assert stats["total_memories"] >= 3
    assert stats["episodic"] >= 2
    assert stats["semantic"] >= 1

