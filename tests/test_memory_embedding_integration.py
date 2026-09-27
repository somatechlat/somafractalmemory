"""Integration tests for the precomputed-embedding contract.

Requires real infrastructure (Postgres). Marked ``integration`` like
tests/test_sanity_service.py.

Proves:
- Precomputed vectors reach the vector store verbatim (never re-hashed).
- Hash fallback records are flagged so search can rank them lower.
- Tenant scoping holds with externally-supplied coords (incl. soft delete).
- DELETE soft-deletes and uniqueness-per-tenant survives re-store.
- Search ranks by vector similarity and demotes hash-fallback hits.
"""

from __future__ import annotations

import pytest
from django.test import TestCase

from somafractalmemory.admin.core.models import Memory, VectorEmbedding
from somafractalmemory.admin.core.services import (
    EMBEDDING_SOURCE_HASH,
    EMBEDDING_SOURCE_PRECOMPUTED,
    get_memory_service,
)

pytestmark = pytest.mark.integration


class RecordingVectorStore:
    """Test spy for the Milvus vector store interface (records insert args)."""

    def __init__(self, dim: int = 256, collection_name: str = "sfm_test"):
        self.dim = dim
        self.collection_name = collection_name
        self.inserted: list[dict] = []
        self.searched: list[list[float]] = []
        self._search_results: list[dict] = []

    def insert(self, coordinate_key, vector, namespace="default", tenant="default"):
        self.inserted.append(
            {
                "coordinate_key": coordinate_key,
                "vector": list(vector),
                "namespace": namespace,
                "tenant": tenant,
            }
        )
        return len(self.inserted)

    def search(self, query_vector, top_k=10, namespace=None, tenant=None):
        self.searched.append(list(query_vector))
        return self._search_results[:top_k]

    def delete(self, coordinate_key, namespace="default", tenant="default"):
        return True

    def health_check(self) -> bool:
        return True


class PrecomputedEmbeddingStoreTest(TestCase):
    """Store must accept precomputed embeddings and flag provenance."""

    def setUp(self):
        self.service = get_memory_service(namespace="test_ns")
        self.store = RecordingVectorStore(dim=self.service.vector_dim)
        self.service.vector_store = self.store

    def test_precomputed_vector_stored_verbatim(self):
        vector = [0.01 * i for i in range(self.service.vector_dim)]
        memory = self.service.store(
            coordinate=(0.1, 0.2, 0.3),
            payload={"text": "hello"},
            tenant="t1",
            embedding=vector,
        )

        assert self.store.inserted, "vector must reach the vector store"
        assert self.store.inserted[0]["vector"] == pytest.approx(vector)
        assert memory.metadata["embedding_source"] == EMBEDDING_SOURCE_PRECOMPUTED

    def test_precomputed_vector_not_rehashed(self):
        vector = [1.0] + [0.0] * (self.service.vector_dim - 1)
        self.service.store(
            coordinate=(0.4, 0.5, 0.6),
            payload={"text": "different words entirely"},
            tenant="t1",
            embedding=vector,
        )
        hashed = self.service.embedder.embed('{"text": "different words entirely"}')
        assert self.store.inserted[0]["vector"] == pytest.approx(vector)
        assert self.store.inserted[0]["vector"] != pytest.approx(hashed)

    def test_vector_embedding_row_records_precomputed_model(self):
        vector = [0.5] * self.service.vector_dim
        self.service.store(
            coordinate=(0.7, 0.8, 0.9),
            payload={"text": "x"},
            tenant="t1",
            embedding=vector,
        )
        row = VectorEmbedding.objects.get(memory__coordinate_key="0.7,0.8,0.9")
        assert row.model_name == "precomputed"
        assert row.vector_dim == self.service.vector_dim

    def test_fallback_is_hash_flagged(self):
        memory = self.service.store(
            coordinate=(0.2, 0.3, 0.4),
            payload={"text": "no vector supplied"},
            tenant="t1",
        )
        assert memory.metadata["embedding_source"] == EMBEDDING_SOURCE_HASH
        assert self.store.inserted[0]["vector"] == pytest.approx(
            self.service.embedder.embed('{"text": "no vector supplied"}')
        )
        row = VectorEmbedding.objects.get(memory__coordinate_key="0.2,0.3,0.4")
        assert row.model_name == "hash-embedder"

    def test_restore_replaces_vector_not_clones(self):
        vector_a = [0.1] * self.service.vector_dim
        vector_b = [0.2] * self.service.vector_dim
        self.service.store((1.0, 1.0, 1.0), {"text": "a"}, tenant="t1", embedding=vector_a)
        self.service.store((1.0, 1.0, 1.0), {"text": "b"}, tenant="t1", embedding=vector_b)
        assert len(self.store.inserted) == 2
        assert self.store.inserted[1]["vector"] == pytest.approx(vector_b)
        assert (
            VectorEmbedding.objects.filter(
                memory__coordinate_key="1.0,1.0,1.0", memory__tenant="t1"
            ).count()
            == 1
        )


class TenantScopedCoordTest(TestCase):
    """Uniqueness-per-tenant must hold with externally-supplied coords."""

    def setUp(self):
        self.service = get_memory_service(namespace="test_ns")

    def test_same_coord_different_tenants_are_isolated(self):
        coord = (0.5, 0.5, 0.5)
        self.service.store(coord, {"text": "for t1"}, tenant="t1")
        self.service.store(coord, {"text": "for t2"}, tenant="t2")

        assert self.service.retrieve(coord, tenant="t1")["payload"] == {"text": "for t1"}
        assert self.service.retrieve(coord, tenant="t2")["payload"] == {"text": "for t2"}
        assert Memory.objects.filter(coordinate_key="0.5,0.5,0.5", is_deleted=False).count() == 2

    def test_delete_is_tenant_scoped(self):
        coord = (0.6, 0.6, 0.6)
        self.service.store(coord, {"text": "for t1"}, tenant="t1")
        self.service.store(coord, {"text": "for t2"}, tenant="t2")

        assert self.service.delete(coord, tenant="t1") is True
        assert self.service.retrieve(coord, tenant="t1") is None
        assert self.service.retrieve(coord, tenant="t2")["payload"] == {"text": "for t2"}

    def test_soft_delete_then_restore_revives_same_row(self):
        coord = (0.7, 0.7, 0.7)
        self.service.store(coord, {"text": "first"}, tenant="t1")
        assert self.service.delete(coord, tenant="t1") is True

        # Soft-deleted: unique (namespace, tenant, coordinate_key) row still held
        row = Memory.objects.get(coordinate_key="0.7,0.7,0.7", tenant="t1")
        assert row.is_deleted is True

        revived = self.service.store(coord, {"text": "second"}, tenant="t1")
        assert revived.is_deleted is False
        assert revived.payload == {"text": "second"}
        assert Memory.objects.filter(coordinate_key="0.7,0.7,0.7", tenant="t1").count() == 1

    def test_delete_twice_returns_false(self):
        coord = (0.8, 0.8, 0.8)
        self.service.store(coord, {"text": "x"}, tenant="t1")
        assert self.service.delete(coord, tenant="t1") is True
        assert self.service.delete(coord, tenant="t1") is False

    def test_search_is_tenant_scoped(self):
        # Exact payload value: the ORM fallback uses JSONB containment (@>),
        # which matches strings by equality.
        self.service.store((0.9, 0.1, 0.1), {"text": "banana"}, tenant="t1")
        self.service.store((0.9, 0.1, 0.2), {"text": "banana"}, tenant="t2")

        results = self.service.search(query="banana", tenant="t1")
        assert results, "tenant t1 must find its own memory"
        coords = {hit["coord"] for hit in results}
        assert coords == {"0.9,0.1,0.1"}

        results_t2 = self.service.search(query="banana", tenant="t2")
        assert {hit["coord"] for hit in results_t2} == {"0.9,0.1,0.2"}


class SearchRankingTest(TestCase):
    """Search must rank by vector similarity and demote hash fallbacks."""

    def setUp(self):
        self.service = get_memory_service(namespace="test_ns")
        self.store = RecordingVectorStore(dim=self.service.vector_dim)
        self.service.vector_store = self.store

    def test_query_embedding_used_verbatim(self):
        query_vec = [0.3] * self.service.vector_dim
        self.service.store(
            (1.1, 1.1, 1.1),
            {"text": "mem"},
            tenant="t1",
            embedding=[0.3] * self.service.vector_dim,
        )
        self.store._search_results = [
            {"coordinate_key": "1.1,1.1,1.1", "score": 0.99, "id": 1},
        ]

        self.service.search(query="", tenant="t1", query_embedding=query_vec)
        assert self.store.searched, "query embedding must reach the vector store"
        assert self.store.searched[0] == pytest.approx(query_vec)

    def test_hash_fallback_hits_rank_lower(self):
        pre_vec = [0.05 * i for i in range(self.service.vector_dim)]
        self.service.store((1.2, 1.2, 1.2), {"text": "real vector"}, tenant="t1", embedding=pre_vec)
        self.service.store((1.3, 1.3, 1.3), {"text": "hashed"}, tenant="t1")

        # Milvus reports the hash hit with a higher raw similarity
        self.store._search_results = [
            {"coordinate_key": "1.3,1.3,1.3", "score": 0.95, "id": 2},
            {"coordinate_key": "1.2,1.2,1.2", "score": 0.50, "id": 1},
        ]

        results = self.service.search(
            query="",
            tenant="t1",
            query_embedding=[0.05 * i for i in range(self.service.vector_dim)],
        )
        assert [hit["coord"] for hit in results] == ["1.2,1.2,1.2", "1.3,1.3,1.3"]
        assert results[0]["embedding_source"] == EMBEDDING_SOURCE_PRECOMPUTED
        assert results[1]["embedding_source"] == EMBEDDING_SOURCE_HASH
        # Precomputed keeps raw score; hash score is penalized (0.95 * 0.25)
        assert results[0]["score"] == pytest.approx(0.50)
        assert results[1]["score"] == pytest.approx(0.95 * 0.25)

    def test_hit_shape_has_coord_score_and_created_at(self):
        self.service.store(
            (1.4, 1.4, 1.4),
            {"text": "shape"},
            tenant="t1",
            embedding=[0.1] * self.service.vector_dim,
        )
        self.store._search_results = [
            {"coordinate_key": "1.4,1.4,1.4", "score": 0.8, "id": 3},
        ]
        results = self.service.search(
            query="", tenant="t1", query_embedding=[0.1] * self.service.vector_dim
        )
        hit = results[0]
        assert hit["coord"] == "1.4,1.4,1.4"
        assert hit["coordinate"] == [1.4, 1.4, 1.4]
        assert hit["payload"] == {"text": "shape"}
        assert isinstance(hit["score"], float)
        assert hit["embedding_source"] == EMBEDDING_SOURCE_PRECOMPUTED
        assert hit["created_at"]

    def test_deleted_memories_excluded_from_search(self):
        self.service.store(
            (1.5, 1.5, 1.5),
            {"text": "gone"},
            tenant="t1",
            embedding=[0.2] * self.service.vector_dim,
        )
        self.service.delete((1.5, 1.5, 1.5), tenant="t1")
        self.store._search_results = [
            {"coordinate_key": "1.5,1.5,1.5", "score": 0.99, "id": 4},
        ]
        results = self.service.search(
            query="", tenant="t1", query_embedding=[0.2] * self.service.vector_dim
        )
        assert results == []
