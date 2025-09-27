from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.storage import InMemoryVectorStore, RedisKeyValueStore


def test_set_importance_syncs_vector_payload():
    kv = RedisKeyValueStore(testing=True)
    vec = InMemoryVectorStore()
    mem = SomaFractalMemoryEnterprise(
        namespace="imp_ns",
        kv_store=kv,
        vector_store=vec,
        graph_store=NetworkXGraphStore(),
        decay_enabled=False,
        reconcile_enabled=False,
    )
    c = (9, 9, 9)
    mem.store_memory(c, {"task": "t", "importance": 0}, memory_type=MemoryType.EPISODIC)
    mem.set_importance(c, importance=5)
    # Verify vector payload reflects updated importance
    found = False
    for rec in vec._points.values():  # type: ignore[attr-defined]
        if rec.payload.get("coordinate") == [9, 9, 9]:
            assert rec.payload.get("importance") == 5
            found = True
            break
    assert found, "Updated payload not found in vector store"
