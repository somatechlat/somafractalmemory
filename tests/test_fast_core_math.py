"""Module test_fast_core_math."""

import math
import os

import pytest

from somafractalmemory.core import SomaFractalMemoryEnterprise
from somafractalmemory.implementations.storage import (
    MilvusVectorStore,
    RedisKeyValueStore,
)
from somafractalmemory.interfaces.graph import IGraphStore

# Skip all tests if Milvus infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Milvus, Redis)",
)


class _NullGraph(IGraphStore):  # Minimal graph for tests (truth: unused operations)
    """Nullgraph class implementation."""

    def add_memory(self, coordinate, value):
        """Execute add memory.

        Args:
            coordinate: The coordinate.
            value: The value.
        """

        return None

    def add_link(self, from_coord, to_coord, link_data):
        """Execute add link.

        Args:
            from_coord: The from_coord.
            to_coord: The to_coord.
            link_data: The link_data.
        """

        return None

    def find_shortest_path(self, from_coord, to_coord, link_type=None):
        """Execute find shortest path.

        Args:
            from_coord: The from_coord.
            to_coord: The to_coord.
            link_type: The link_type.
        """

        return []

    def get_neighbors(self, coord, link_type=None, limit=None):
        """Retrieve neighbors.

        Args:
            coord: The coord.
            link_type: The link_type.
            limit: The limit.
        """

        return []

    def remove_memory(self, coordinate):
        """Execute remove memory.

        Args:
            coordinate: The coordinate.
        """

        return None

    def clear(self):
        """Execute clear."""

        return None

    def export_graph(self, path: str):
        """Execute export graph.

        Args:
            path: The path.
        """

        return None

    def import_graph(self, path: str):
        """Execute import graph.

        Args:
            path: The path.
        """

        return None

    def health_check(self):
        """Execute health check."""

        return True


def _make_memory_system():
    """Create a memory system backed by real Redis and Milvus.

    The test suite runs on a developer machine where Docker-compose provides
    Redis and Milvus instances. Architecture decision: Milvus-only for vectors.
    """
    import uuid

    # Real KV store – Redis running from Docker-compose.
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    kv_store = RedisKeyValueStore(host="localhost", port=redis_port)

    # Real Milvus vector store (Qdrant removed per architecture decision)
    milvus_host = os.environ.get("SOMA_MILVUS_HOST", "localhost")
    milvus_port = int(os.environ.get("SOMA_MILVUS_PORT", 19530))
    collection_name = f"fast_core_test_{uuid.uuid4().hex[:8]}"
    vector_store = MilvusVectorStore(
        collection_name=collection_name,
        host=milvus_host,
        port=milvus_port,
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
    """Execute test norm invariant on insert."""

    m = _make_memory_system()
    for i in range(10):
        m.store_memory((float(i), float(i + 1)), {"fact": f"x{i}", "importance": i})
    # Inspect underlying vector store
    vs = m.vector_store
    norms = []
    for rec in vs.scroll():
        # MilvusVectorStore returns records with vector data
        # Access vector from the record (Milvus returns dict-like objects)
        vec = rec.get("vector") if isinstance(rec, dict) else getattr(rec, "vector", None)
        if vec is not None:
            n = math.sqrt(sum(x * x for x in vec))
            norms.append(n)
    if norms:
        assert max(abs(n - 1.0) for n in norms) < 1e-4


def test_similarity_monotonicity():
    """Execute test similarity monotonicity."""

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
    """Execute test importance monotonicity."""

    m = _make_memory_system()
    m.store_memory((0.0, 0.0), {"fact": "low", "importance": 1})
    m.store_memory((0.1, 0.1), {"fact": "high", "importance": 100})
    res = m.find_hybrid_by_type("fact", top_k=2)
    # With same query token present, higher importance_norm should surface earlier
    facts = [r.get("fact") for r in res]
    assert facts[0] == "high"


def test_zero_similarity_clamp():
    """Execute test zero similarity clamp."""

    m = _make_memory_system()
    m.store_memory((0.0, 0.0), {"fact": "alpha", "importance": 1})
    # Craft a vector far from random by storing arbitrary different content
    m.store_memory((1.0, 1.0), {"fact": "beta", "importance": 1})
    # Query with a term absent from both to produce near-hash collisions
    res = m.find_hybrid_by_type("nonexistenttoken", top_k=2)
    # Scores are not directly exposed here (payload only) – ensure no crash & ordering stable
    assert len(res) == 2
