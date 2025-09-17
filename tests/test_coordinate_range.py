from somafractalmemory.core import MemoryType
from somafractalmemory.factory import create_memory_system, MemoryMode


def test_find_by_coordinate_range(tmp_path):
    mem = create_memory_system(MemoryMode.LOCAL_AGENT, "box_ns", config={"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "q.db")}})
    pts = [
        ((0,0,0), {"d": 0}),
        ((1,1,1), {"d": 1}),
        ((2,2,2), {"d": 2}),
        ((3,3,3), {"d": 3}),
    ]
    for c, p in pts:
        mem.store_memory(c, p, memory_type=MemoryType.EPISODIC)
    found = mem.find_by_coordinate_range((1,1,1), (2,2,2))
    coords = {tuple(m["coordinate"]) for m in found}
    assert coords == {(1.0,1.0,1.0), (2.0,2.0,2.0)}

def test_find_by_coordinate_range_with_type(tmp_path):
    mem = create_memory_system(MemoryMode.LOCAL_AGENT, "box_type", config={"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "q.db")}})
    mem.store_memory((1,1,1), {"d": 1}, memory_type=MemoryType.EPISODIC)
    mem.store_memory((2,2,2), {"d": 2}, memory_type=MemoryType.SEMANTIC)
    # Only episodic within box should return the first
    found = mem.find_by_coordinate_range((1,1,1), (2,2,2), memory_type=MemoryType.EPISODIC)
    coords = {tuple(m["coordinate"]) for m in found}
    assert coords == {(1.0,1.0,1.0)}
