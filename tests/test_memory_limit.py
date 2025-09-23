import time

import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},
        "memory_enterprise": {"max_memory_size": 3},
    }
    return create_memory_system(MemoryMode.DEVELOPMENT, "limit_ns", config=config)


def test_memory_limit_prunes_old_low_importance(mem: SomaFractalMemoryEnterprise):
    coords = [(0, 0, i) for i in range(5)]
    # Insert 5 episodic memories with varying importance and timestamp order
    for i, c in enumerate(coords):
        mem.store_memory(
            c, {"i": i, "importance": 1 if i < 3 else 5}, memory_type=MemoryType.EPISODIC
        )
        time.sleep(0.01)

    stats = mem.memory_stats()
    assert stats["total_memories"] <= 3
    # Ensure at least one high-importance item survived
    important = [
        m for m in mem.retrieve_memories(MemoryType.EPISODIC) if m.get("importance", 0) >= 5
    ]
    assert len(important) >= 1
