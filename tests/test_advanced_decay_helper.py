import time

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise, _coord_to_key
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.prediction import NoPredictionProvider
from somafractalmemory.implementations.storage import InMemoryVectorStore, RedisKeyValueStore


def test_advanced_decay_removes_non_essential_fields():
    kv = RedisKeyValueStore(testing=True)
    mem = SomaFractalMemoryEnterprise(
        namespace="decay_ns",
        kv_store=kv,
        vector_store=InMemoryVectorStore(),
        graph_store=NetworkXGraphStore(),
        prediction_provider=NoPredictionProvider(),
        decay_enabled=False,
        reconcile_enabled=False,
    )
    c = (1, 1, 1)
    payload = {"task": "old", "importance": 0, "scratch": "tmp", "low_importance": True}
    mem.store_memory(c, payload, memory_type=MemoryType.EPISODIC)

    # Force very old creation and last_accessed timestamps to trigger decay_score > 2
    data_key, meta_key = _coord_to_key(mem.namespace, c)
    now = time.time()
    very_old = now - (3600 * 24 * 30)
    kv.hset(
        meta_key,
        mapping={
            b"creation_timestamp": str(very_old).encode("utf-8"),
            b"last_accessed_timestamp": str(very_old).encode("utf-8"),
        },
    )

    mem._apply_decay_to_all()
    out = mem.retrieve(c)
    assert out is not None
    # Should keep only essential keys
    for k in ["task", "scratch", "low_importance"]:
        assert k not in out, f"{k} should be decayed"
    assert "memory_type" in out and "coordinate" in out and "importance" in out
