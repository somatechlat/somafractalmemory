from somafractalmemory.core import SomaFractalMemoryEnterprise as SomaFractalMemory
from somafractalmemory.implementations.storage import InMemoryKeyValueStore, InMemoryVectorStore


class _NoopGraph:
    def find_shortest_path(self, a, b, t=None):
        return []


class _NoopPrediction:
    def predict(self, value):
        return None, 0.0


def test_eviction_score_updates_on_importance_change():
    kv = InMemoryKeyValueStore()
    vec = InMemoryVectorStore()
    graph = _NoopGraph()
    pred = _NoopPrediction()

    mem = SomaFractalMemory(
        namespace="ux_ns",
        kv_store=kv,
        vector_store=vec,
        graph_store=graph,
        prediction_provider=pred,
        max_memory_size=10,
    )

    coord = (0, 0, 0)
    mem.store(coord, {"text": "hello", "importance": 1})

    ev_key = f"{mem.namespace}:eviction_index"
    before = kv.zrange(ev_key, 0, -1, withscores=True)
    assert before, "Expected an eviction zset entry after store"
    # Increase importance and update
    mem.set_importance(coord, 50)
    after = kv.zrange(ev_key, 0, -1, withscores=True)
    # Scores should change (importance increased -> score decreases)
    assert before != after
