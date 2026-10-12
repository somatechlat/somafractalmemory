"""B20 / B21 write-contract: accepted fields land in columns, and a failed
vector insert aborts the whole write.

Real infrastructure only (operator law 8): every row assertion runs against
live Postgres through the Django ORM. The vector-store seam is exercised with
a test double ONLY where a failure must be injected — the established pattern
in ``test_vector_clone_on_delete_failure.py`` (a broken Milvus cannot be
requested on demand; anything else would mock away the system under test).
"""

from __future__ import annotations

import pytest

from somafractalmemory.admin.core.models import Memory, VectorEmbedding
from somafractalmemory.admin.core.services import MemoryService

# --- database gate --------------------------------------------------------
# pytest-django blocks connection.ensure_connection() at import time, so the
# reachability probe authenticates with the configured DSN via psycopg instead
# of a bare TCP open (something else may listen on that port).


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
        "write-contract tests must run against the real database"
    ),
)


class ExplodingInsertStore:
    """TEST DOUBLE: delete ok, insert always fails.

    The only way to force a Milvus insert failure without breaking the shared
    Milvus instance. Same pattern as test_vector_clone_on_delete_failure.py.
    """

    collection_name = "test_collection"

    def __init__(self) -> None:
        self.insert_calls: list[dict] = []
        self.delete_calls: list[str] = []

    def delete(self, coordinate_key: str, namespace: str = "default", tenant: str = "default"):
        self.delete_calls.append(coordinate_key)
        return True

    def delete_by_id(self, milvus_id):
        return True

    def insert(self, **kwargs):
        self.insert_calls.append(kwargs)
        raise RuntimeError("simulated Milvus insert failure")

    def search(self, **kwargs):
        return []

    def health_check(self) -> bool:
        return True


class SilentInsertStore:
    """TEST DOUBLE: healthy insert, used to isolate column-write behaviour."""

    collection_name = "test_collection"

    def __init__(self) -> None:
        self._next_id = 1

    def delete(self, coordinate_key: str, namespace: str = "default", tenant: str = "default"):
        return True

    def delete_by_id(self, milvus_id):
        return True

    def insert(self, **kwargs):
        pk = self._next_id
        self._next_id += 1
        return pk

    def search(self, **kwargs):
        return []

    def health_check(self) -> bool:
        return True


@requires_db
@pytest.mark.django_db(transaction=True)
class TestStoreWritesAcceptedFields:
    """B20: importance / belief_* are columns, not dropped request fields."""

    def test_importance_is_written_not_left_at_default(self):
        service = MemoryService(namespace="unit_write_importance")
        service.vector_store = SilentInsertStore()
        coord = (1.0, 2.0, 3.0)

        service.store(
            coord,
            {"text": "high stakes"},
            memory_type="episodic",
            tenant="t-b20",
            importance=0.87,
        )

        row = Memory.objects.get(
            namespace="unit_write_importance",
            coordinate_key=Memory.coord_to_key(coord),
        )
        assert row.importance == pytest.approx(0.87), (
            "B20: an accepted importance value must reach the column — "
            "a store request must not leave it at 0.0"
        )

    def test_belief_confidence_and_polarity_are_written(self):
        service = MemoryService(namespace="unit_write_belief")
        service.vector_store = SilentInsertStore()
        coord = (4.0, 5.0, 6.0)

        service.store(
            coord,
            {"text": "the sky is green"},
            memory_type="belief",
            tenant="t-b20",
            importance=0.42,
            belief_confidence=0.93,
            belief_polarity="negative",
        )

        row = Memory.objects.get(
            namespace="unit_write_belief",
            coordinate_key=Memory.coord_to_key(coord),
        )
        assert row.memory_type == "belief"
        assert row.belief_confidence == pytest.approx(0.93)
        assert row.belief_polarity == "negative"
        assert row.importance == pytest.approx(0.42)

    def test_working_memory_type_is_persisted(self):
        service = MemoryService(namespace="unit_write_wm")
        service.vector_store = SilentInsertStore()
        coord = (7.0, 8.0, 9.0)

        service.store(
            coord,
            {"text": "scratch"},
            memory_type="working_memory",
            tenant="t-b20",
            importance=0.11,
        )

        row = Memory.objects.get(
            namespace="unit_write_wm",
            coordinate_key=Memory.coord_to_key(coord),
        )
        assert row.memory_type == Memory.MemoryType.WORKING_MEMORY

    def test_zero_importance_is_still_written_as_zero(self):
        """Accepting 0.0 must not be confused with 'field was ignored'."""
        service = MemoryService(namespace="unit_write_zero")
        service.vector_store = SilentInsertStore()
        coord = (1.5, 2.5, 3.5)

        service.store(coord, {"text": "low"}, tenant="t-b20", importance=0.0)

        row = Memory.objects.get(
            namespace="unit_write_zero",
            coordinate_key=Memory.coord_to_key(coord),
        )
        assert row.importance == pytest.approx(0.0)


@requires_db
@pytest.mark.django_db(transaction=True)
class TestMilvusInsertFailureAbortsWrite:
    """B21 / law 7: a failed vector insert aborts the transaction."""

    def test_failed_insert_raises_and_leaves_no_orm_row(self):
        service = MemoryService(namespace="unit_b21_abort")
        store = ExplodingInsertStore()
        service.vector_store = store
        coord = (10.0, 20.0, 30.0)

        with pytest.raises(RuntimeError, match="simulated Milvus insert failure"):
            service.store(
                coord,
                {"text": "must not survive"},
                tenant="t-b21",
                importance=0.5,
            )

        assert not Memory.objects.filter(
            namespace="unit_b21_abort",
            coordinate_key=Memory.coord_to_key(coord),
        ).exists(), (
            "B21: the ORM row must be rolled back — a memory without its "
            "vector is data loss, not a degraded success"
        )
        assert store.insert_calls, "the insert attempt must actually have happened"

    def test_failed_insert_leaves_existing_row_untouched(self):
        service = MemoryService(namespace="unit_b21_keep")
        coord = (11.0, 21.0, 31.0)

        keeper = SilentInsertStore()
        service.vector_store = keeper
        service.store(coord, {"version": 1}, tenant="t-b21", importance=0.3)
        assert Memory.objects.filter(
            namespace="unit_b21_keep", coordinate_key=Memory.coord_to_key(coord)
        ).exists()

        service.vector_store = ExplodingInsertStore()
        with pytest.raises(RuntimeError, match="simulated Milvus insert failure"):
            service.store(coord, {"version": 2}, tenant="t-b21", importance=0.9)

        row = Memory.objects.get(
            namespace="unit_b21_keep",
            coordinate_key=Memory.coord_to_key(coord),
        )
        assert row.payload == {
            "version": 1
        }, "B21: the failed update must roll back — the previous write stands"
        assert row.importance == pytest.approx(0.3)

    def test_failed_insert_leaves_no_vector_embedding_row(self):
        service = MemoryService(namespace="unit_b21_noemb")
        service.vector_store = ExplodingInsertStore()
        coord = (12.0, 22.0, 32.0)

        with pytest.raises(RuntimeError, match="simulated Milvus insert failure"):
            service.store(coord, {"text": "x"}, tenant="t-b21")

        assert not VectorEmbedding.objects.filter(
            memory__namespace="unit_b21_noemb",
            memory__coordinate_key=Memory.coord_to_key(coord),
        ).exists()

    def test_precomputed_embedding_without_vector_store_refuses(self):
        """Law 7: a precomputed embedding is never silently dropped."""
        service = MemoryService(namespace="unit_b21_nostore")
        service.vector_store = None
        coord = (13.0, 23.0, 33.0)

        with pytest.raises(RuntimeError):
            service.store(
                coord,
                {"text": "has a real vector"},
                tenant="t-b21",
                embedding=[0.0] * service.vector_dim,
            )
        assert not Memory.objects.filter(
            namespace="unit_b21_nostore",
            coordinate_key=Memory.coord_to_key(coord),
        ).exists()
