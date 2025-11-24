from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system
from somafractalmemory.implementations.storage import InMemoryVectorStore


def test_on_demand_inmemory_vector_toggle(tmp_path):
    # Use a real Redis instance (exposed on host port 40022) instead of the fakeredis testing shim.
    mem = create_memory_system(
        MemoryMode.EVENTED_ENTERPRISE,
        "od_mem",
        config={
            "vector": {"backend": "memory"},
            "redis": {"host": "localhost", "port": 40022},
        },
    )
    assert isinstance(mem.vector_store, InMemoryVectorStore)
    c = (1, 2, 3)
    mem.store_memory(c, {"task": "x"}, memory_type=MemoryType.EPISODIC)
    res = mem.recall("x", top_k=1)
    assert isinstance(res, list) and res
