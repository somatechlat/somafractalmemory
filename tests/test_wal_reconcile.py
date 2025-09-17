import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


def test_wal_reconcile_on_vector_failure(tmp_path, monkeypatch):
    mem: SomaFractalMemoryEnterprise = create_memory_system(
        MemoryMode.LOCAL_AGENT,
        "wal_ns",
        config={"redis": {"testing": True}, "qdrant": {"path": str(tmp_path / "q.db")}},
    )

    calls = {"upsert": 0}

    real_upsert = mem.vector_store.upsert

    def flaky_upsert(points):
        calls["upsert"] += 1
        if calls["upsert"] == 1:
            raise RuntimeError("simulated failure")
        return real_upsert(points)

    monkeypatch.setattr(mem.vector_store, "upsert", flaky_upsert)

    coord = (1, 1, 1)
    mem.store_memory(coord, {"d": 1}, memory_type=MemoryType.EPISODIC)

    # After failure, WAL should contain a failed/pending entry
    wal_keys = list(mem.kv_store.scan_iter(f"{mem.namespace}:wal:*"))
    assert wal_keys, "WAL entry not created"

    # Fix upsert and reconcile
    monkeypatch.setattr(mem.vector_store, "upsert", real_upsert)
    mem._reconcile_once()

    # WAL entries should be committed
    import pickle
    for k in wal_keys:
        raw = mem.kv_store.get(k)
        if raw:
            entry = pickle.loads(raw)
            assert entry.get("status") == "committed"

