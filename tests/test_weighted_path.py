from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_weighted_shortest_path(tmp_path):
    mem = create_memory_system(
        MemoryMode.LOCAL_AGENT,
        "weighted_ns",
        config={
            "redis": {"testing": True},
            "qdrant": {"path": str(tmp_path / "q.db")},
        },
    )
    a, b, c = (0, 0, 0), (1, 0, 0), (2, 0, 0)
    mem.store_memory(a, {"d": 1}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(b, {"d": 2}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c, {"d": 3}, memory_type=MemoryType.EPISODIC)
    # Two paths: direct a->c weight 5, or a->b->c with weight 1+1
    mem.link_memories(a, c, link_type="related", weight=5.0)
    mem.link_memories(a, b, link_type="related", weight=1.0)
    mem.link_memories(b, c, link_type="related", weight=1.0)
    path = mem.find_shortest_path(a, c, link_type="related")
    assert path == [a, b, c]


def make_mem(ns: str = "ver_ns") -> SomaFractalMemoryEnterprise:
    return create_memory_system(MemoryMode.LOCAL_AGENT, ns)
