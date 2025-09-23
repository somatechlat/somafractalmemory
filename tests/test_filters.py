from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_find_hybrid_by_type_with_filters(tmp_path):
    mem = create_memory_system(
        MemoryMode.DEVELOPMENT,
        "filters_ns",
        config={
            "redis": {"testing": True},
            "qdrant": {"path": str(tmp_path / "q.db")},
        },
    )
    mem.store_memory((1, 1, 1), {"task": "alpha", "tag": "keep"}, memory_type=MemoryType.EPISODIC)
    mem.store_memory((2, 2, 2), {"task": "alpha", "tag": "drop"}, memory_type=MemoryType.EPISODIC)
    res = mem.find_hybrid_by_type("alpha", top_k=5, filters={"tag": "keep"})
    assert isinstance(res, list)
    assert res and res[0]["tag"] == "keep"
