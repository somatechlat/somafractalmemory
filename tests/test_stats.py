import threading

import psycopg2
import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system
from somafractalmemory.implementations.storage import PostgresKeyValueStore


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},
    }
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "stats_ns", config=config)


def test_memory_stats_counts(mem: SomaFractalMemoryEnterprise):
    assert mem.memory_stats()["total_memories"] == 0
    c1, c2, c3 = (1, 1, 1), (2, 2, 2), (3, 3, 3)
    mem.store_memory(c1, {"d": 1}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c2, {"d": 2}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c3, {"f": 3}, memory_type=MemoryType.SEMANTIC)
    stats = mem.memory_stats()
    assert stats["total_memories"] >= 3
    assert stats["episodic"] >= 2
    assert stats["semantic"] >= 1


class _FakeCursor:
    def __init__(self, conn, rows):
        self._conn = conn
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *_args, **_kwargs):
        if self._conn.fail_next:
            self._conn.fail_next = False
            self._conn.closed = 1
            raise psycopg2.InterfaceError("connection already closed")

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return None


class _FakeConnection:
    def __init__(self, *, fail_once: bool, rows: list[tuple[str]]):
        self.fail_next = fail_once
        self.rows = rows
        self.closed = 0

    def cursor(self):
        return _FakeCursor(self, self.rows)

    def close(self):
        self.closed = 1


def test_postgres_scan_iter_recovers_from_closed_connection():
    rows = [("stats_ns:1:data",), ("stats_ns:2:data",)]
    failing_conn = _FakeConnection(fail_once=True, rows=rows)
    healthy_conn = _FakeConnection(fail_once=False, rows=rows)
    connections = [failing_conn, healthy_conn]

    store: PostgresKeyValueStore = object.__new__(PostgresKeyValueStore)
    store._TABLE_NAME = "kv_store"  # type: ignore[attr-defined]
    store._url = "postgresql://unused"  # type: ignore[attr-defined]
    store._sslmode = None  # type: ignore[attr-defined]
    store._sslrootcert = None  # type: ignore[attr-defined]
    store._sslcert = None  # type: ignore[attr-defined]
    store._sslkey = None  # type: ignore[attr-defined]
    store._lock = threading.RLock()  # type: ignore[attr-defined]
    store._conn = None  # type: ignore[attr-defined]

    def _fake_ensure(self):
        if self._conn is None or getattr(self._conn, "closed", 0):
            self._conn = connections.pop(0)

    store._ensure_connection = _fake_ensure.__get__(store, PostgresKeyValueStore)  # type: ignore[attr-defined]
    store._ensure_table = (lambda self: None).__get__(store, PostgresKeyValueStore)  # type: ignore[attr-defined]

    results = list(store.scan_iter("stats_ns:*:data"))

    assert results == ["stats_ns:1:data", "stats_ns:2:data"]
    assert healthy_conn.closed == 0
