from somafractalmemory.factory import MemoryMode, create_memory_system


def test_lock_redlock_stub(tmp_path):
    cfg = {
        "qdrant": {"path": str(tmp_path / "q.db")},
        "redis": {"testing": True},
        "memory_enterprise": {},
        # locks config passed to kv store via redis config for now
    }
    mem = create_memory_system(MemoryMode.LOCAL_AGENT, "lock_ns", config=cfg)
    lock = mem.acquire_lock("test_lock", timeout=1)
    assert lock is not None
    with lock:
        pass
