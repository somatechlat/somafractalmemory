import time

import numpy as np
import pytest
from redis.exceptions import ConnectionError

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {"qdrant": {"path": str(tmp_path / "qdrant.db")}, "redis": {"testing": True}}
    return create_memory_system(MemoryMode.LOCAL_AGENT, "test_ns", config=config)


def test_basic_store_and_retrieve(mem: SomaFractalMemoryEnterprise):
    coordinate = (1.0, 2.0, 3.0)
    data = {"test": "data"}
    mem.store_memory(coordinate, data)
    retrieved = mem.retrieve(coordinate)
    assert retrieved is not None
    assert retrieved["test"] == "data"
    assert "memory_type" in retrieved
    assert retrieved["memory_type"] == MemoryType.EPISODIC.value


def test_distributed_lock(mem: SomaFractalMemoryEnterprise):
    lock_name = "my_distributed_lock"
    lock = mem.acquire_lock(lock_name, timeout=1)
    assert lock is not None
    with lock:
        # The lock is acquired
        pass
    # The lock is released after the 'with' block


def test_store_vector_only(mem: SomaFractalMemoryEnterprise):
    vector = np.random.rand(mem.vector_dim).astype("float32")
    mem.store_vector_only((0, 0, 0), vector, payload={"meta": "data"})
    # Verification would require a search, but we're just testing the call
    results = mem.recall("a query", top_k=1)
    assert len(results) > 0


def test_backend_failover(mem: SomaFractalMemoryEnterprise, monkeypatch):
    # Simulate Redis connection error
    def mock_ping_fail():
        raise ConnectionError

    monkeypatch.setattr(mem.kv_store, "health_check", mock_ping_fail)

    health = mem.health_check()
    assert not health["kv_store"]

    # Simulate Qdrant failure
    def mock_qdrant_fail():
        raise Exception("Qdrant down")

    monkeypatch.setattr(mem.vector_store, "health_check", mock_qdrant_fail)

    health = mem.health_check()
    assert not health["vector_store"]


def test_memory_decay(tmp_path):
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},
        "memory_enterprise": {
            "decay_thresholds_seconds": [1],
            "decayable_keys_by_level": [["test_field"]],
            "pruning_interval_seconds": 1,
        },
    }
    mem = create_memory_system(MemoryMode.LOCAL_AGENT, "decaytest", config=config)

    coordinate = (1, 1, 1)
    data = {"test_field": "value", "permanent_field": "value2"}
    mem.store_memory(coordinate, data)

    # Backdate creation timestamp to trigger decay without sleeping
    meta_key = f"{mem.namespace}:{repr(coordinate)}:meta"
    mem.kv_store.hset(
        meta_key, mapping={b"creation_timestamp": str(time.time() - 2).encode("utf-8")}
    )
    # Run a deterministic single decay pass
    mem.run_decay_once()
    retrieved = mem.retrieve(coordinate)
    assert retrieved is not None
    assert "test_field" not in retrieved
    assert "permanent_field" in retrieved
