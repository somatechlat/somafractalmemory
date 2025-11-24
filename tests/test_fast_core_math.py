import math

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.storage import (
    QdrantVectorStore,
    RedisKeyValueStore,
)
from somafractalmemory.interfaces.graph import IGraphStore


class _NullGraph(IGraphStore):  # Minimal stub for tests (truth: unused operations)
    def add_memory(self, coordinate, value):
        return None

    def add_link(self, from_coord, to_coord, link_data):
        return None

    def find_shortest_path(self, from_coord, to_coord, link_type=None):
        return []

    def get_neighbors(self, coord, link_type=None, limit=None):
        return []

    def remove_memory(self, coordinate):
        return None

    def clear(self):
        return None

    def export_graph(self, path: str):
        return None

    def import_graph(self, path: str):
        return None

    def health_check(self):
        return True


def _make_memory_system():
    """Create a memory system backed by real Redis and a temporary on‑disk Qdrant.

    The test suite runs on a developer machine where Docker‑compose provides a
    Redis instance on ``localhost:40022``. For the vector store we create a
    Qdrant client that stores its data under a temporary directory created via
    ``tempfile.mkdtemp`` – this guarantees isolation between test runs without
    needing the pytest ``tmp_path`` fixture.
    """
    import tempfile
    from pathlib import Path

    # Real KV store – Redis running from Docker‑compose.
    kv_store = RedisKeyValueStore(host="localhost", port=40022)

    # Temporary on‑disk Qdrant instance.
    qdrant_dir = Path(tempfile.mkdtemp())
    vector_store = QdrantVectorStore(
        collection_name="fast_core_test", path=str(qdrant_dir / "qdrant.db")
    )

    return SomaFractalMemoryEnterprise(
        namespace="test",
        kv_store=kv_store,
        vector_store=vector_store,
        graph_store=_NullGraph(),
        vector_dim=32,
        decay_enabled=False,
        reconcile_enabled=False,
    )


def test_norm_invariant_on_insert():
    m = _make_memory_system()
    for i in range(10):
        m.store_memory((float(i), float(i + 1)), {"fact": f"x{i}", "importance": i})
    # Inspect underlying vector store
    vs = m.vector_store
    norms = []
    for rec in vs.scroll():
        # QdrantVectorStore returns records that always expose a ``vector`` attribute.
        # The previous fallback for the removed ``InMemoryVectorStore`` is no longer needed.
        vec = rec.vector
        n = math.sqrt(sum(x * x for x in vec))
        norms.append(n)
    assert max(abs(n - 1.0) for n in norms) < 1e-4


def test_similarity_monotonicity():
    m = _make_memory_system()
    # Insert a target memory identical to query, and a random different one
    target_payload = {"fact": "perfect", "importance": 5}
    other_payload = {"fact": "other", "importance": 5}
    m.store_memory((0.0, 0.1), target_payload)
    m.store_memory((1.0, 2.0), other_payload)
    # Query using the text of target payload to ensure higher similarity
    res = m.find_hybrid_by_type("perfect", top_k=2)
    facts = [r.get("fact") for r in res]
    assert facts[0] == "perfect"


def test_importance_monotonicity():
    m = _make_memory_system()
    m.store_memory((0.0, 0.0), {"fact": "low", "importance": 1})
    m.store_memory((0.1, 0.1), {"fact": "high", "importance": 100})
    res = m.find_hybrid_by_type("fact", top_k=2)
    # With same query token present, higher importance_norm should surface earlier
    facts = [r.get("fact") for r in res]
    assert facts[0] == "high"


def test_zero_similarity_clamp():
    m = _make_memory_system()
    m.store_memory((0.0, 0.0), {"fact": "alpha", "importance": 1})
    # Craft a vector far from random by storing arbitrary different content
    m.store_memory((1.0, 1.0), {"fact": "beta", "importance": 1})
    # Query with a term absent from both to produce near-hash collisions
    res = m.find_hybrid_by_type("nonexistenttoken", top_k=2)
    # Scores are not directly exposed here (payload only) – ensure no crash & ordering stable
    assert len(res) == 2
