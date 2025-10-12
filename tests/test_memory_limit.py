import time

import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    # Use a unique namespace per test run using timestamp to avoid collisions with other tests
    ns = f"limit_ns_{int(time.time()*1000)}"
    config = {
        "qdrant": {"path": str(tmp_path / f"{ns}.db")},
        "redis": {"testing": True},
        "memory_enterprise": {"max_memory_size": 3},
    }
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, ns, config=config)


def test_memory_limit_prunes_old_low_importance(mem: SomaFractalMemoryEnterprise):
    coords = [(0, 0, i) for i in range(5)]
    # Insert 5 episodic memories with varying importance and timestamp order
    for i, c in enumerate(coords):
        mem.store_memory(
            c, {"i": i, "importance": 1 if i < 3 else 5}, memory_type=MemoryType.EPISODIC
        )
        time.sleep(0.01)

    # Force an additional pruning pass (in case timing prevented immediate enforcement)
    mem._enforce_memory_limit()  # type: ignore[attr-defined]
    stats = mem.memory_stats()
    assert stats["total_memories"] <= 3, stats
    # Ensure at least one high-importance item survived
    important = [
        m for m in mem.retrieve_memories(MemoryType.EPISODIC) if m.get("importance", 0) >= 5
    ]
    assert len(important) >= 1
