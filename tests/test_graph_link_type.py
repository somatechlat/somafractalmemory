from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_shortest_path_with_link_type(tmp_path):
    cfg = {"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "q.db")}}
    mem = create_memory_system(MemoryMode.LOCAL_AGENT, "lt_ns", config=cfg)
    a, b, c = (1, 1, 1), (2, 2, 2), (3, 3, 3)
    mem.store_memory(a, {"d": 1}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(b, {"d": 2}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c, {"d": 3}, memory_type=MemoryType.EPISODIC)

    mem.link_memories(a, b, link_type="related")
    mem.link_memories(b, c, link_type="unrelated")

    # Path via 'related' only should fail to reach c
    path_rel = mem.find_shortest_path(a, c, link_type="related")
    assert path_rel == [] or path_rel == [a]  # no path to c

    # Without filter, path exists
    path_any = mem.find_shortest_path(a, c)
    assert path_any == [a, b, c]
