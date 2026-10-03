"""Vector cloning on delete-then-insert must be impossible.

When a write updates a coordinate that already has a vector, the old vector is
deleted first. If that delete fails and the code inserts anyway, one coordinate
ends up with two vectors ("vector cloning").

VIBE Coding Rules: no mocks. The failure is injected with a test double that
implements the vector-store surface and raises on delete — that is the only way
to exercise a failing delete without a broken Milvus.
"""

from __future__ import annotations

import pytest

from somafractalmemory.admin.core.models import Memory
from somafractalmemory.admin.core.services import MemoryService


def _database_available() -> bool:
    """True when Django can open a real Postgres connection with its settings.

    Tests that need a credential must skip when that credential is absent.
    """
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from django.db import connection

            connection.ensure_connection()
            connection.close()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _database_available(),
    reason="Postgres credential not available; skip DB-backed vector-clone tests",
)


class ExplodingDeleteStore:
    """TEST DOUBLE: vector store whose delete always fails.

    Insert is recorded so the test can prove the clone path never runs.
    """

    collection_name = "test_collection"

    def __init__(self) -> None:
        self.insert_calls: list[dict] = []

    def delete(self, coordinate_key: str, namespace: str = "default", tenant: str = "default"):
        raise RuntimeError("vector delete failed")

    def insert(self, **kwargs):
        self.insert_calls.append(kwargs)
        raise AssertionError("insert must not run after a failed delete")


@requires_db
@pytest.mark.django_db(transaction=True)
class TestFailedVectorDelete:
    """A failed delete must raise and leave the row untouched."""

    def test_failed_delete_raises_and_never_inserts(self):
        service = MemoryService(namespace="unit_clone_fresh")
        store = ExplodingDeleteStore()
        service.vector_store = store
        coord = (1.0, 2.0, 3.0)

        with pytest.raises(RuntimeError, match="vector delete failed"):
            service.store(coord, {"text": "hello"})

        assert store.insert_calls == [], "insert after a failed delete is vector cloning"
        coord_key = Memory.coord_to_key(coord)
        assert not Memory.objects.filter(
            namespace="unit_clone_fresh", coordinate_key=coord_key
        ).exists()

    def test_failed_delete_leaves_existing_row_untouched(self):
        service = MemoryService(namespace="unit_clone_update")
        coord = (4.0, 5.0, 6.0)
        coord_key = Memory.coord_to_key(coord)

        # First write with no vector store: the ORM row exists.
        service.vector_store = None
        service.store(coord, {"version": 1})

        service.vector_store = ExplodingDeleteStore()
        with pytest.raises(RuntimeError, match="vector delete failed"):
            service.store(coord, {"version": 2})

        memory = Memory.objects.get(namespace="unit_clone_update", coordinate_key=coord_key)
        assert memory.payload == {"version": 1}
        assert service.vector_store.insert_calls == []


class TestStoreSourceDoesNotSwallowDeleteFailure:
    """Static guard: the delete-then-insert path must not `except: pass`."""

    def test_store_source_has_no_silent_delete_pass(self):
        import ast
        from pathlib import Path

        from somafractalmemory.admin.core import services as services_mod

        source = Path(services_mod.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        # Find MemoryService.store and ensure vector delete is not wrapped in
        # `except Exception: pass` immediately before insert.
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name != "store":
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Try):
                    continue
                for handler in child.handlers:
                    body_is_pass = len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass)
                    if not body_is_pass:
                        continue
                    # Does this try-block contain a .delete( call?
                    calls_delete = any(
                        isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "delete"
                        for n in ast.walk(child)
                    )
                    assert not calls_delete, (
                        "MemoryService.store still has `except: pass` around "
                        "vector_store.delete — that is vector cloning"
                    )
        else:
            # at least one store method must exist
            assert any(isinstance(n, ast.FunctionDef) and n.name == "store" for n in ast.walk(tree))
