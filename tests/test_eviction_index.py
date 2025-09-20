import time

from somafractalmemory.core import SomaFractalMemoryEnterprise as SomaFractalMemory
from somafractalmemory.implementations.storage import InMemoryKeyValueStore, InMemoryVectorStore


class _NoopGraph:
    def find_shortest_path(self, a, b, t=None):
        return []


class _NoopPrediction:
    pass


def test_eviction_index_prunes_low_importance(tmp_path):
    kv = InMemoryKeyValueStore()
    vec = InMemoryVectorStore()
    graph = _NoopGraph()
    pred = _NoopPrediction()

    mem = SomaFractalMemory(
        namespace="limit_ns",
        kv_store=kv,
        vector_store=vec,
        graph_store=graph,
        prediction_provider=pred,
        max_memory_size=2,
    )

    # Insert three memories with varying importance and timestamps
    mem.store((0, 0, 0), {"text": "low importance", "importance": 1})
    time.sleep(0.01)
    mem.store((0, 0, 1), {"text": "low importance 2", "importance": 1})
    time.sleep(0.01)
    # High importance should survive pruning
    mem.store((0, 0, 2), {"text": "high importance", "importance": 100})

    # Enforce memory limit
    mem._enforce_memory_limit()

    # After pruning, high importance item should exist
    found = []
    for k in mem.kv_store.scan_iter(f"{mem.namespace}:*:data"):
        raw = mem.kv_store.get(k)
        obj = mem._deserialize(raw)
        found.append((k, obj.get("importance")))

    # There should be at most 2 items and one with importance 100
    assert any(imp == 100 for _, imp in found)
