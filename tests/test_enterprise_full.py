import pytest
import numpy as np
import time
from somafractalmemory.core import SomaFractalMemoryEnterprise, MemoryType, SomaFractalMemoryError

def test_basic_store_and_retrieve(tmp_path):
    mem = SomaFractalMemoryEnterprise(
        namespace="test_ns",
        redis_nodes=[{"host": "localhost", "port": 6379}],
        qdrant_path=str(tmp_path / "qdrant.db"),
        config_file="config.yaml",
        decay_thresholds_seconds=[1],
        decayable_keys_by_level=[["test_field"]],
        pruning_interval_seconds=1
    )
    coord = (1.0, 2.0)
    data = {"test_field": "value", "other": 123}
    mem.store_memory(coord, data, memory_type=MemoryType.EPISODIC)
    out = mem.retrieve(coord)
    assert out["test_field"] == "value"
    assert out["other"] == 123

def test_distributed_lock(tmp_path):
    mem = SomaFractalMemoryEnterprise(namespace="locktest", redis_nodes=[{"host": "localhost", "port": 6379}], qdrant_path=str(tmp_path / "qdrant.db"))
    def critical_section(x):
        return x + 1
    result = mem.with_lock("test", critical_section, 41)
    assert result == 42

def test_store_vector_only(tmp_path):
    mem = SomaFractalMemoryEnterprise(namespace="vectest", redis_nodes=[{"host": "localhost", "port": 6379}], qdrant_path=str(tmp_path / "qdrant.db"))
    coord = (3.0, 4.0)
    vec = np.random.rand(mem.vector_dim).astype(np.float32)
    mem.store_vector_only(coord, vec)
    # Should not raise

def test_backend_failover(tmp_path, monkeypatch):
    mem = SomaFractalMemoryEnterprise(namespace="failover", redis_nodes=[{"host": "localhost", "port": 6379}], qdrant_path=str(tmp_path / "qdrant.db"))
    # Simulate Redis down
    monkeypatch.setattr(mem.redis, "ping", lambda: (_ for _ in ()).throw(Exception("fail")))
    try:
        mem.check_dependencies()
    except SomaFractalMemoryError:
        pass
    # Simulate Qdrant down
    monkeypatch.setattr(mem.qdrant, "get_collections", lambda: (_ for _ in ()).throw(Exception("fail")))
    with pytest.raises(SomaFractalMemoryError):
        mem.check_dependencies()

def test_memory_decay(tmp_path):
    mem = SomaFractalMemoryEnterprise(
        namespace="decaytest",
        redis_nodes=[{"host": "localhost", "port": 6379}],
        qdrant_path=str(tmp_path / "qdrant.db"),
        decay_thresholds_seconds=[1],
        decayable_keys_by_level=[["test_field"]],
        pruning_interval_seconds=1
    )
    coord = (5.0, 6.0)
    data = {"test_field": "decayme", "other": 456}
    mem.store_memory(coord, data, memory_type=MemoryType.EPISODIC)
    time.sleep(2)
    # Wait for decay thread
    for _ in range(5):
        out = mem.retrieve(coord)
        if "test_field" not in out:
            break
        time.sleep(1)
    assert "test_field" not in mem.retrieve(coord)
