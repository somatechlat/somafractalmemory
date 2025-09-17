import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.implementations.graph import NetworkXGraphStore
from somafractalmemory.implementations.prediction import NoPredictionProvider
from somafractalmemory.implementations.storage import InMemoryVectorStore


@pytest.fixture
def memory_system():
    kv_store = None  # Use in-memory for tests
    vector_store = InMemoryVectorStore()
    graph_store = NetworkXGraphStore()
    prediction_provider = NoPredictionProvider()
    return SomaFractalMemoryEnterprise(
        namespace="test_ns",
        kv_store=kv_store,
        vector_store=vector_store,
        graph_store=graph_store,
        prediction_provider=prediction_provider,
    )


def test_store_and_recall(memory_system):
    coord = (1.0, 2.0, 3.0)
    payload = {"task": "test task", "importance": 1}
    assert memory_system.store_memory(coord, payload, MemoryType.EPISODIC)
    results = memory_system.recall("test task", top_k=1)
    assert len(results) > 0
    assert results[0]["task"] == "test task"


def test_link_and_path(memory_system):
    coord1 = (1.0, 2.0, 3.0)
    coord2 = (4.0, 5.0, 6.0)
    memory_system.store_memory(coord1, {"fact": "start"}, MemoryType.SEMANTIC)
    memory_system.store_memory(coord2, {"fact": "end"}, MemoryType.SEMANTIC)
    memory_system.link_memories(coord1, coord2, "related")
    path = memory_system.find_shortest_path(coord1, coord2)
    assert len(path) >= 2


def test_delete(memory_system):
    coord = (1.0, 2.0, 3.0)
    payload = {"task": "delete test"}
    memory_system.store_memory(coord, payload, MemoryType.EPISODIC)
    memory_system.delete(coord)
    results = memory_system.recall("delete test", top_k=1)
    assert len(results) == 0
