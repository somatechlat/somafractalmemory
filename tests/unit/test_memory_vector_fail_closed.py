"""Memory write/search must fail closed when the vector side cannot answer.

Proves the seam contract the adversarial review demanded:

- a write whose Milvus insert fails does NOT persist the ORM row and does NOT
  ack ok=True (store() raises; MemoryStoreResponse is never built);
- a failed insert does NOT destroy the previously indexed vector
  (insert-then-swap: the old vector is only removed by id after the new one
  exists);
- distance is converted to similarity metric-aware (L2 is a distance; COSINE
  and IP are already similarities) and ranking follows the converted score;
- a precomputed query vector never silently becomes exact-text ORM search and
  importance is never labelled as similarity.

Test doubles implement the vector-store surface so a failing Milvus can be
exercised without a broken Milvus — the same pattern as
``test_vector_clone_on_delete_failure.py``.
"""

from __future__ import annotations

import math

import pytest

from somafractalmemory.admin.core.implementations.milvus_vector import _hit_similarity
from somafractalmemory.admin.core.models import Memory
from somafractalmemory.admin.core.services import (
    MemoryService,
    VectorIndexUnavailable,
)

# --- database gate --------------------------------------------------------
# pytest-django blocks connection.ensure_connection() at import time
# ("Database access not allowed"), so that check is always False under pytest.
# Authenticate with the configured DSN via psycopg2 instead — a real
# credential handshake, not a bare TCP open (something else may listen there).


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
                connect_timeout=1,
            )
        except ImportError:
            import psycopg2

            conn = psycopg2.connect(
                host=cfg["HOST"],
                port=int(cfg["PORT"]),
                dbname=cfg["NAME"],
                user=cfg["USER"],
                password=cfg["PASSWORD"],
                connect_timeout=1,
            )
        conn.close()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _database_reachable(),
    reason=(
        "Postgres credential refused at the configured "
        "SOMA_DB_HOST/SOMA_DB_PORT/SOMA_DB_USER — DB-backed tests cannot run"
    ),
)


class ExplodingInsertStore:
    """TEST DOUBLE: delete ok, insert always fails.

    Also records whether the superseded vector was removed before the insert
    — insert-then-swap forbids that.
    """

    collection_name = "test_collection"

    def __init__(self) -> None:
        self.insert_calls: list[dict] = []
        self.deleted_keys: list[str] = []
        self.deleted_ids: list[object] = []

    def delete(self, coordinate_key: str, namespace: str = "default", tenant: str = "default"):
        self.deleted_keys.append(coordinate_key)
        return True

    def delete_by_id(self, milvus_id):
        self.deleted_ids.append(milvus_id)
        return True

    def insert(self, **kwargs):
        self.insert_calls.append(kwargs)
        raise RuntimeError("simulated Milvus insert failure")

    def search(self, **kwargs):
        return []

    def health_check(self) -> bool:
        return True


class RecordingSwapStore:
    """TEST DOUBLE: successful store, records the swap order."""

    collection_name = "test_collection"

    def __init__(self, dim: int = 8) -> None:
        self.dim = dim
        self._next_id = 1
        self.rows: dict[object, dict] = {}
        self.events: list[tuple[str, object]] = []

    def delete(self, coordinate_key: str, namespace: str = "default", tenant: str = "default"):
        self.events.append(("delete_by_key", coordinate_key))
        for pk, row in list(self.rows.items()):
            if row["coordinate_key"] == coordinate_key:
                del self.rows[pk]
        return True

    def delete_by_id(self, milvus_id):
        self.events.append(("delete_by_id", milvus_id))
        self.rows.pop(milvus_id, None)
        return True

    def insert(self, coordinate_key, vector, namespace="default", tenant="default"):
        self.events.append(("insert", coordinate_key))
        pk = self._next_id
        self._next_id += 1
        self.rows[pk] = {
            "coordinate_key": coordinate_key,
            "vector": list(vector),
            "namespace": namespace,
            "tenant": tenant,
        }
        return pk

    def search(self, query_vector, top_k=10, namespace=None, tenant=None):
        self.events.append(("search", tuple(query_vector[:3])))
        scored = []
        q = list(query_vector)
        for pk, row in self.rows.items():
            if namespace is not None and row["namespace"] != namespace:
                continue
            if tenant is not None and row["tenant"] != tenant:
                continue
            num = sum(a * b for a, b in zip(q, row["vector"], strict=False))
            nq = math.sqrt(sum(a * a for a in q)) or 1.0
            nr = math.sqrt(sum(a * a for a in row["vector"])) or 1.0
            scored.append(
                {
                    "id": pk,
                    "coordinate_key": row["coordinate_key"],
                    "namespace": row["namespace"],
                    "tenant": row["tenant"],
                    "score": num / (nq * nr),
                }
            )
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    def health_check(self) -> bool:
        return True


class FilteringStore:
    """TEST DOUBLE: returns hits whose coordinates are then filtered out."""

    collection_name = "test_collection"

    def delete(self, coordinate_key, namespace="default", tenant="default"):
        return True

    def delete_by_id(self, milvus_id):
        return True

    def insert(self, **kwargs):
        return 1

    def search(self, **kwargs):
        return [
            {
                "id": 1,
                "coordinate_key": "missing-from-orm",
                "namespace": "ns",
                "tenant": "t",
                "score": 0.9,
            }
        ]

    def health_check(self) -> bool:
        return True


class EmptyStore:
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


class TestHitSimilarityConvention:
    """Distance -> similarity at ONE place, metric-aware (C2-2)."""

    def test_cosine_self_hit_is_one(self):
        assert _hit_similarity(1.0, "COSINE") == pytest.approx(1.0)

    def test_cosine_needs_no_inversion(self):
        # live probe: flipped self-hit raw distance is -1.0 (true cosine)
        assert _hit_similarity(-1.0, "COSINE") == pytest.approx(0.0)
        assert _hit_similarity(0.0, "COSINE") == pytest.approx(0.0)

    def test_ip_passes_through_clamped(self):
        assert _hit_similarity(1.0, "IP") == pytest.approx(1.0)
        assert _hit_similarity(2.0, "IP") == pytest.approx(1.0)
        assert _hit_similarity(-1.0, "IP") == pytest.approx(0.0)

    def test_l2_zero_distance_is_one(self):
        assert _hit_similarity(0.0, "L2") == pytest.approx(1.0)

    def test_l2_inverts_so_desc_sort_is_correct(self):
        near = _hit_similarity(0.02, "L2")
        far = _hit_similarity(2.0, "L2")
        assert near > far, "L2 distance must not survive as a similarity"

    def test_l2_is_clamped_into_unit_interval(self):
        assert 0.0 <= _hit_similarity(10.0, "L2") <= 1.0

    def test_none_stays_none(self):
        assert _hit_similarity(None, "COSINE") is None


@requires_db
@pytest.mark.django_db(transaction=True)
class TestInsertThenSwap:
    """C2-1: a failed insert must not destroy the old vector."""

    def test_insert_failure_raises_and_never_deletes_by_key(self):
        store = ExplodingInsertStore()
        service = MemoryService(namespace="unit_fail_closed")
        service.vector_store = store
        with pytest.raises(RuntimeError, match="simulated Milvus insert failure"):
            service.store((1.0, 2.0, 3.0), {"text": "hello"})
        # The old vector must not be removed before the new one exists.
        assert (
            store.deleted_keys == []
        ), "delete-before-insert is permanent vector loss on a failed insert"

    def test_swap_records_old_vector_by_id_after_insert(self):
        service = MemoryService(namespace="unit_swap")
        store = RecordingSwapStore(dim=service.vector_dim)
        service.vector_store = store
        vec1 = [1.0] + [0.0] * (service.vector_dim - 1)
        vec2 = [0.0, 1.0] + [0.0] * (service.vector_dim - 2)
        service.store((9.0, 9.0, 9.0), {"text": "a"}, embedding=vec1)
        service.store((9.0, 9.0, 9.0), {"text": "b"}, embedding=vec2)
        kinds = [e[0] for e in store.events]
        insert_at = kinds.index("insert")
        assert "delete_by_id" in kinds
        delete_at = kinds.index("delete_by_id")
        assert insert_at < delete_at, "must insert before removing the superseded vector"
        assert (
            "delete_by_key" not in kinds
        ), "delete-by-key would also remove the vector just inserted"
        # exactly one live vector for the coordinate after the swap
        live = [row for row in store.rows.values() if row["coordinate_key"] == "9.0,9.0,9.0"]
        assert len(live) == 1
        assert live[0]["vector"] == pytest.approx(vec2)


@requires_db
@pytest.mark.django_db(transaction=True)
class TestWriteFailClosed:
    """Gate 1: no ORM row, no ok=True when the vector cannot be indexed."""

    def test_failed_insert_does_not_persist_orm_row(self):
        service = MemoryService(namespace="unit_no_orphan_row")
        service.vector_store = ExplodingInsertStore()
        coord = (4.0, 5.0, 6.0)
        with pytest.raises(RuntimeError, match="simulated Milvus insert failure"):
            service.store(coord, {"text": "must not persist"})
        assert not Memory.objects.filter(
            namespace="unit_no_orphan_row",
            coordinate_key=Memory.coord_to_key(coord),
        ).exists()

    def test_failed_insert_does_not_lose_existing_vector(self):
        """C2-1 acceptance: update with a failing insert keeps the old vector."""
        service = MemoryService(namespace="unit_keep_old_vector")
        coord = (7.0, 8.0, 9.0)
        v1 = [1.0] + [0.0] * (service.vector_dim - 1)
        v2 = [0.0, 1.0] + [0.0] * (service.vector_dim - 2)

        keeper = RecordingSwapStore(dim=service.vector_dim)
        service.vector_store = keeper
        service.store(coord, {"version": 1}, embedding=list(v1))
        assert len(keeper.rows) == 1
        old_pk = next(iter(keeper.rows))

        service.vector_store = ExplodingInsertStore()
        with pytest.raises(RuntimeError, match="simulated Milvus insert failure"):
            service.store(coord, {"version": 2}, embedding=list(v2))

        # ORM rolled back to the first write; the first vector is still indexed.
        memory = Memory.objects.get(
            namespace="unit_keep_old_vector",
            coordinate_key=Memory.coord_to_key(coord),
        )
        assert memory.payload == {"version": 1}
        assert old_pk in keeper.rows, "failed update must not delete the previously indexed vector"
        assert keeper.rows[old_pk]["vector"] == pytest.approx(v1)

    def test_precomputed_embedding_without_vector_store_refuses(self):
        service = MemoryService(namespace="unit_no_store_precomputed")
        service.vector_store = None
        with pytest.raises(VectorIndexUnavailable):
            service.store((1.0, 1.0, 1.0), {"text": "x"}, embedding=[0.0] * service.vector_dim)
        assert not Memory.objects.filter(namespace="unit_no_store_precomputed").exists()


class TestVectorQueryFailsClosed:
    """C2-3: three lies replaced with a typed refusal (no DB required)."""

    def test_vector_store_search_raises_fails_closed(self):
        from ninja.errors import HttpError

        service = MemoryService(namespace="unit_fc_raise")
        service.vector_store = RaisingSearchStore()
        with pytest.raises(HttpError) as exc:
            service.search(
                query="",
                query_embedding=[0.0] * service.vector_dim,
            )
        assert exc.value.status_code == 503

    def test_vector_store_empty_result_fails_closed(self):
        from ninja.errors import HttpError

        service = MemoryService(namespace="unit_fc_empty")
        service.vector_store = EmptyStore()
        with pytest.raises(HttpError) as exc:
            service.search(query="q", query_embedding=[0.0] * service.vector_dim)
        assert exc.value.status_code == 503

    @requires_db
    @pytest.mark.django_db(transaction=True)
    def test_vector_hits_all_filtered_fails_closed(self):
        from ninja.errors import HttpError

        service = MemoryService(namespace="unit_fc_filtered")
        service.vector_store = FilteringStore()
        with pytest.raises(HttpError) as exc:
            service.search(query="q", query_embedding=[0.0] * service.vector_dim)
        assert exc.value.status_code == 503

    def test_precomputed_query_without_vector_store_fails_closed(self):
        from ninja.errors import HttpError

        service = MemoryService(namespace="unit_fc_nostore")
        service.vector_store = None
        with pytest.raises(HttpError) as exc:
            service.search(query="q", query_embedding=[0.0] * service.vector_dim)
        assert exc.value.status_code == 503


@requires_db
@pytest.mark.django_db(transaction=True)
class TestTextOnlyStillServesFromOrm:
    def test_text_only_query_serves_from_orm_without_importance_as_score(self):
        service = MemoryService(namespace="unit_text_orm")
        service.vector_store = None
        # ORM __contains on payload is exact JSON containment: the query must
        # equal the field value. Use the seam `text` key.
        service.store((0.1, 0.2, 0.3), {"text": "apple"})
        results = service.search(query="apple", tenant="default")
        assert results, "text-only query must still serve from the ORM path"
        assert results[0]["payload"]["text"] == "apple"
        for row in results:
            # importance is NOT similarity
            assert row["score"] is None
            assert "importance" in row
            assert row.get("vector_indexed") is False


# --- live metric ordering (C2-2 acceptance) --------------------------------


def _milvus_reachable() -> bool:
    try:
        import socket

        from somafractalmemory.settings.model import resolve_optional

        host = resolve_optional("SOMA_MILVUS_HOST")
        port = resolve_optional("SOMA_MILVUS_PORT")
        if not host or not port:
            return False
        with socket.create_connection((host, int(port)), timeout=1.0):
            return True
    except Exception:
        return False


requires_milvus = pytest.mark.skipif(
    not _milvus_reachable(),
    reason="Milvus at the configured SOMA_MILVUS_HOST/SOMA_MILVUS_PORT is not reachable",
)


@requires_milvus
class TestRecallOrderMatchesMetric:
    """C2-2 acceptance: under EACH metric the nearer vector ranks first.

    Runs against the live Milvus. L2 is the metric that is inverted today if
    the raw distance is sorted DESCENDING without conversion.
    """

    def _search_order(self, metric: str, dim: int) -> list[str]:
        """Insert near/far, search, convert at _hit_similarity, sort DESC.

        Uses raw pymilvus for the metric sweep (SOMA_SIMILARITY_METRIC is one
        operator setting) and the production conversion at the one place.
        """
        import uuid

        from pymilvus import DataType, MilvusClient

        from somafractalmemory.settings.model import milvus_uri, resolve_setting

        client = MilvusClient(
            uri=milvus_uri(),
            timeout=float(resolve_setting("SOMA_MILVUS_TIMEOUT_S")),
        )
        coll = f"probe_order_{metric.lower()}_{uuid.uuid4().hex[:8]}"
        schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field("coordinate_key", DataType.VARCHAR, max_length=512)
        schema.add_field("namespace", DataType.VARCHAR, max_length=255)
        schema.add_field("tenant", DataType.VARCHAR, max_length=255)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dim)
        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type=metric,
            params={"nlist": int(resolve_setting("SOMA_MILVUS_NLIST"))},
        )
        client.create_collection(collection_name=coll, schema=schema, index_params=index_params)
        try:
            query = [1.0] + [0.0] * (dim - 1)
            near = [0.9, 0.1] + [0.0] * (dim - 2)
            far = [0.0, 1.0] + [0.0] * (dim - 2)
            client.insert(
                collection_name=coll,
                data=[
                    {
                        "coordinate_key": "near",
                        "namespace": "probe",
                        "tenant": "probe",
                        "vector": near,
                    },
                    {
                        "coordinate_key": "far",
                        "namespace": "probe",
                        "tenant": "probe",
                        "vector": far,
                    },
                ],
            )
            client.flush(collection_name=coll)
            raw = client.search(
                collection_name=coll,
                data=[query],
                anns_field="vector",
                search_params={
                    "metric_type": metric,
                    "params": {"nprobe": int(resolve_setting("SOMA_MILVUS_NPROBE"))},
                },
                limit=2,
                filter='namespace == "probe"',
                output_fields=["coordinate_key"],
            )
            hits = []
            for group in raw:
                for hit in group:
                    entity = hit.get("entity") or {}
                    similarity = _hit_similarity(hit.get("distance", hit.get("score")), metric)
                    hits.append(
                        {
                            "coordinate_key": entity.get("coordinate_key"),
                            "score": similarity,
                        }
                    )
            # Production sort is DESCENDING on the converted similarity.
            hits.sort(key=lambda h: (-float(h["score"]), str(h["coordinate_key"])))
            return [h["coordinate_key"] for h in hits]
        finally:
            client.drop_collection(collection_name=coll)

    def test_cosine_nearer_vector_first(self):
        assert self._search_order("COSINE", 8)[0] == "near"

    def test_ip_nearer_vector_first(self):
        assert self._search_order("IP", 8)[0] == "near"

    def test_l2_nearer_vector_first(self):
        assert self._search_order("L2", 8)[0] == "near"
