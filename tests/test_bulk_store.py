from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_store_memories_bulk_core(tmp_path):
    """Test bulk storage of multiple memories."""
    # Use the real Redis service (exposed on host port 40022) instead of the fakeredis testing shim.
    mem = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE,
        "bulk_core",
        config={
            "redis": {"host": "localhost", "port": 40022},
            "qdrant": {"path": str(tmp_path / "q.db")},
        },
    )
    items = [
        ((1, 1, 1), {"content": "first memory"}, MemoryType.EPISODIC),
        ((2, 2, 2), {"content": "second memory"}, MemoryType.SEMANTIC),
    ]
    mem.store_memories_bulk(items)

    # Verify stored memories
    first = mem.retrieve((1, 1, 1))
    second = mem.retrieve((2, 2, 2))
    assert first is not None
    assert second is not None
    assert first["content"] == "first memory"
    assert second["content"] == "second memory"
