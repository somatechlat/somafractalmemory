"""B17 / law 5: degraded recall must FLAG, never return a silent ``[]``.

Callers must be able to tell "no history" (degraded=False, memories=[]) from
"the vector path could not answer" (degraded=True). Every row assertion runs
against live Postgres; the vector-store seam uses a test double ONLY to inject
a failure (the established pattern in ``test_vector_clone_on_delete_failure.py``).
"""

from __future__ import annotations

import pytest

from somafractalmemory.admin.core.services import MemoryService


def _database_reachable() -> bool:
    try:
        from django.conf import settings

        cfg = settings.DATABASES["default"]
        try:
            import psycopg

            conn = psycopg.connect(
                host=cfg["HOST"],
                port=int(cfg["PORT"]),
                dbname=cfg["NAME"],
                user=cfg["USER"],
                password=cfg["PASSWORD"],
                connect_timeout=2,
            )
        except ImportError:
            import psycopg2

            conn = psycopg2.connect(
                host=cfg["HOST"],
                port=int(cfg["PORT"]),
                dbname=cfg["NAME"],
                user=cfg["USER"],
                password=cfg["PASSWORD"],
                connect_timeout=2,
            )
        conn.close()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _database_reachable(),
    reason=(
        "Postgres credential refused at the configured SOMA_DB_HOST/SOMA_DB_PORT — "
        "degraded-search tests must run against the real database"
    ),
)


class RaisingSearchStore:
    """TEST DOUBLE: search raises like a dead Milvus."""

    collection_name = "test_collection"

    def delete(self, coordinate_key, namespace="default", tenant="default"):
        return True

    def delete_by_id(self, milvus_id):
        return True

    def insert(self, **kwargs):
        return 1

    def search(self, **kwargs):
        raise RuntimeError("milvus down")

    def health_check(self) -> bool:
        return False


class EmptySearchStore:
    """TEST DOUBLE: healthy vector index that simply has no matches."""

    collection_name = "test_collection"

    def delete(self, coordinate_key, namespace="default", tenant="default"):
        return True

    def delete_by_id(self, milvus_id):
        return True

    def insert(self, **kwargs):
        return 1

    def search(self, **kwargs):
        return []

    def health_check(self) -> bool:
        return True


class OneHitStore:
    """TEST DOUBLE: healthy vector index returning one known coordinate."""

    collection_name = "test_collection"

    def __init__(self, coordinate_key: str) -> None:
        self.coordinate_key = coordinate_key

    def delete(self, coordinate_key, namespace="default", tenant="default"):
        return True

    def delete_by_id(self, milvus_id):
        return True

    def insert(self, **kwargs):
        return 1

    def search(self, **kwargs):
        return [{"id": 1, "coordinate_key": self.coordinate_key, "score": 0.9}]

    def health_check(self) -> bool:
        return True


@requires_db
@pytest.mark.django_db(transaction=True)
class TestVectorFailureIsFlaggedNotSilent:
    """B17: a vector-path failure returns degraded=True + reason, never []."""

    def test_vector_search_failure_sets_degraded_and_reason(self):
        service = MemoryService(namespace="unit_deg_raise")
        service.vector_store = RaisingSearchStore()

        outcome = service.search(query="anything", tenant="t-deg")

        assert outcome["degraded"] is True, "B17: a failed vector path must flag itself"
        assert outcome["degraded_reason"], "B17: degraded=True without a reason is not actionable"
        assert "milvus down" in outcome["degraded_reason"]
        assert isinstance(outcome["memories"], list)

    def test_vector_failure_never_returns_bare_empty_list(self):
        """The old contract returned [] — indistinguishable from 'no history'."""
        service = MemoryService(namespace="unit_deg_bare")
        service.vector_store = RaisingSearchStore()

        outcome = service.search(query="nothing matches this", tenant="t-deg")

        # memories may be empty after the ORM fallback, but the envelope must
        # carry the degradation — the caller must never see a bare [].
        assert set(outcome) >= {"memories", "degraded", "degraded_reason"}
        assert outcome["degraded"] is True

    def test_vector_failure_with_text_query_falls_back_but_stays_flagged(self):
        service = MemoryService(namespace="unit_deg_fallback")
        service.vector_store = RaisingSearchStore()
        service.store((1.0, 1.0, 1.0), {"text": "apple"}, tenant="t-deg")

        outcome = service.search(query="apple", tenant="t-deg")

        assert outcome["memories"], "the ORM fallback should still find the row"
        assert (
            outcome["degraded"] is True
        ), "B17: a fallback path after a vector failure is still degraded"
        assert outcome["degraded_reason"]

    def test_vector_only_query_with_dead_store_is_empty_but_flagged(self):
        service = MemoryService(namespace="unit_deg_veconly")
        service.vector_store = RaisingSearchStore()

        outcome = service.search(
            query="",
            tenant="t-deg",
            query_embedding=[0.0] * service.vector_dim,
        )

        assert (
            outcome["memories"] == []
        ), "a vector-only query must not browse every memory on fallback"
        assert (
            outcome["degraded"] is True
        ), "B17: an empty answer to a vector query must be flagged, not silent"


@requires_db
@pytest.mark.django_db(transaction=True)
class TestHealthySearchIsNotDegraded:
    def test_healthy_vector_search_reports_degraded_false(self):
        service = MemoryService(namespace="unit_deg_ok")
        service.store(
            (2.0, 2.0, 2.0),
            {"text": "real"},
            tenant="t-deg",
            embedding=[0.1] * service.vector_dim,
        )
        service.vector_store = OneHitStore("2.0,2.0,2.0")

        outcome = service.search(
            query="",
            tenant="t-deg",
            query_embedding=[0.1] * service.vector_dim,
        )

        assert outcome["degraded"] is False
        assert outcome["degraded_reason"] is None
        assert outcome["memories"], "the stored memory must be recallable"

    def test_genuine_empty_result_is_not_degraded(self):
        """'No history' must look different from 'store unavailable'."""
        service = MemoryService(namespace="unit_deg_empty")
        service.vector_store = EmptySearchStore()

        outcome = service.search(
            query="",
            tenant="t-deg",
            query_embedding=[0.0] * service.vector_dim,
        )

        assert outcome["memories"] == []
        assert (
            outcome["degraded"] is False
        ), "a healthy store with no matches is an honest empty, not degraded"

    def test_text_only_path_without_vector_store_is_flagged(self):
        """Law 5: recall without the vector index is a limited answer."""
        service = MemoryService(namespace="unit_deg_nostore")
        service.vector_store = None
        service.store((3.0, 3.0, 3.0), {"text": "plum"}, tenant="t-deg")

        outcome = service.search(query="plum", tenant="t-deg")

        assert outcome["memories"], "text recall should still work"
        assert outcome["degraded"] is True
        assert outcome["degraded_reason"]


@requires_db
@pytest.mark.django_db(transaction=True)
class TestSearchEnvelopeShape:
    def test_envelope_exposes_memories_degraded_and_reason(self):
        service = MemoryService(namespace="unit_deg_shape")
        service.vector_store = RaisingSearchStore()

        outcome = service.search(query="x", tenant="t-deg")

        assert isinstance(outcome, dict)
        assert isinstance(outcome["memories"], list)
        assert isinstance(outcome["degraded"], bool)
        assert outcome["degraded_reason"] is None or isinstance(outcome["degraded_reason"], str)

    def test_stats_count_belief_and_working_memory(self):
        service = MemoryService(namespace="unit_deg_stats")
        service.vector_store = None

        service.store((4.0, 4.0, 4.0), {"text": "b"}, tenant="t-deg", memory_type="belief")
        service.store((5.0, 5.0, 5.0), {"text": "w"}, tenant="t-deg", memory_type="working_memory")
        service.store((6.0, 6.0, 6.0), {"text": "e"}, tenant="t-deg", memory_type="episodic")

        stats = service.stats()
        assert stats["belief"] == 1
        assert stats["working_memory"] == 1
        assert stats["episodic"] == 1
        assert stats["total_memories"] == 3
