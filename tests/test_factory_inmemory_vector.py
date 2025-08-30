from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.implementations.storage import InMemoryVectorStore
from somafractalmemory.core import MemoryType


def test_on_demand_inmemory_vector_toggle(tmp_path):
    mem = create_memory_system(
        MemoryMode.ON_DEMAND,
        "od_mem",
        config={
            "vector": {"backend": "inmemory"},
            "redis": {"testing": True},
        },
    )
    assert isinstance(mem.vector_store, InMemoryVectorStore)
    c = (1, 2, 3)
    mem.store_memory(c, {"task": "x"}, memory_type=MemoryType.EPISODIC)
    res = mem.recall("x", top_k=1)
    assert isinstance(res, list) and res
