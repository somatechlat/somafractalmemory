import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {
        "qdrant": {"path": str(tmp_path / "qdrant.db")},
        "redis": {"testing": True},
    }
    return create_memory_system(MemoryMode.LOCAL_AGENT, "agent_features_ns", config=config)


def test_set_importance_and_get_important(mem: SomaFractalMemoryEnterprise):
    c1 = (0.1, 0.1, 0.1)
    c2 = (0.2, 0.2, 0.2)
    mem.store_memory(c1, {"task": "low"}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(c2, {"task": "high"}, memory_type=MemoryType.EPISODIC)
    mem.set_importance(c1, importance=1)
    mem.set_importance(c2, importance=5)
    top = mem.get_important(n=1)
    assert top and top[0].get("importance") == 5


def test_consolidate_memories_creates_semantic(mem: SomaFractalMemoryEnterprise):
    c = (1.1, 2.2, 3.3)
    mem.store_memory(c, {"task": "event"}, memory_type=MemoryType.EPISODIC)
    mem.consolidate_memories(window_seconds=3600)
    semantics = mem.retrieve_memories(MemoryType.SEMANTIC)
    assert any(m.get("consolidated_from") == c for m in semantics)


def test_share_memory_with(tmp_path):
    cfg1 = {"qdrant": {"path": str(tmp_path / "q1.db")}, "redis": {"testing": True}}
    cfg2 = {"qdrant": {"path": str(tmp_path / "q2.db")}, "redis": {"testing": True}}
    m1 = create_memory_system(MemoryMode.LOCAL_AGENT, "ns1", config=cfg1)
    m2 = create_memory_system(MemoryMode.LOCAL_AGENT, "ns2", config=cfg2)
    c = (9.9, 9.9, 9.9)
    m1.store_memory(c, {"fact": "shared"}, memory_type=MemoryType.SEMANTIC)
    m1.share_memory_with(m2)
    got = m2.retrieve(c)
    assert got is not None
    assert got.get("fact") == "shared"


def test_find_hybrid_with_context(mem: SomaFractalMemoryEnterprise):
    c = (5.5, 5.5, 5.5)
    mem.store_memory(c, {"task": "email client"}, memory_type=MemoryType.EPISODIC)
    res = mem.find_hybrid_with_context("email", {"channel": "gmail"}, top_k=3)
    assert isinstance(res, list)
    assert any(isinstance(r, dict) for r in res)
