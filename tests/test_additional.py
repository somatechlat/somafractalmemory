import numpy as np
import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system
from somafractalmemory.implementations.graph import NetworkXGraphStore


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},
        "memory_enterprise": {
            "pruning_interval_seconds": 1,
            "decay_thresholds_seconds": [1],
            "decayable_keys_by_level": [["scratch"]],
        },
    }
    return create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "additional_ns", config=config)


def test_delete_removes_graph_and_kv(mem: SomaFractalMemoryEnterprise):
    coord = (9, 9, 9)
    mem.store_memory(coord, {"data": "x"})
    assert mem.retrieve(coord) is not None
    assert isinstance(mem.graph_store, NetworkXGraphStore)
    assert mem.graph_store.graph.has_node(coord)
    mem.delete(coord)
    assert mem.retrieve(coord) is None
    assert not mem.graph_store.graph.has_node(coord)


def test_versioning_roundtrip(mem: SomaFractalMemoryEnterprise):
    coord = (7, 7, 7)
    payload = {"d": 1}
    mem.store_memory(coord, payload)
    mem.save_version(coord)
    versions = mem.get_versions(coord)
    assert len(versions) >= 1
    assert versions[0]["d"] == 1


def test_hooks_fire_and_resilient(mem: SomaFractalMemoryEnterprise):
    seen = []

    def before_store(data, coordinate, memory_type):
        seen.append(("before_store", coordinate))

    def after_store(data, coordinate, memory_type):
        seen.append(("after_store", coordinate))

    def before_recall(*args, **kwargs):
        seen.append(("before_recall",))
        raise RuntimeError("ignored in hooks")

    def after_recall(*args, **kwargs):
        seen.append(("after_recall",))

    mem.set_hook("before_store", before_store)
    mem.set_hook("after_store", after_store)
    mem.set_hook("before_recall", before_recall)
    mem.set_hook("after_recall", after_recall)

    coord = (1.2, 3.4, 5.6)
    mem.remember({"task": "t"}, coordinate=coord, memory_type=MemoryType.EPISODIC)
    results = mem.recall("t", top_k=1)
    assert isinstance(results, list)
    assert ("before_store", coord) in seen and ("after_store", coord) in seen
    assert any(ev[0] == "before_recall" for ev in seen)
    assert any(ev[0] == "after_recall" for ev in seen)


def test_embed_fallback_deterministic(mem: SomaFractalMemoryEnterprise):
    # Force fallback path
    mem.tokenizer = None
    mem.model = None
    v1 = mem.embed_text("hello world")
    v2 = mem.embed_text("hello world")
    assert v1.shape == (1, mem.vector_dim)
    assert v2.shape == (1, mem.vector_dim)
    assert np.allclose(v1, v2)
