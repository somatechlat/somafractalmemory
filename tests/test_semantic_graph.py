import pytest

from somafractalmemory.core import MemoryType, SomaFractalMemoryEnterprise
from somafractalmemory.factory import MemoryMode, create_memory_system
from somafractalmemory.implementations.graph import NetworkXGraphStore


@pytest.fixture
def mem(tmp_path) -> SomaFractalMemoryEnterprise:
    config = {"qdrant": {"path": str(tmp_path / "qdrant.db")}, "redis": {"testing": True}}
    return create_memory_system(MemoryMode.DEVELOPMENT, "test_graph", config=config)


def test_semantic_graph_basic(mem: SomaFractalMemoryEnterprise):
    # Ensure the graph store is the correct type for this test
    assert isinstance(mem.graph_store, NetworkXGraphStore)

    coord1 = (1, 2, 3)
    coord2 = (4, 5, 6)
    mem.store_memory(coord1, {"data": "memory 1"}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(coord2, {"data": "memory 2"}, memory_type=MemoryType.SEMANTIC)

    graph = mem.graph_store.graph  # Access the graph directly
    assert coord1 in graph
    assert coord2 in graph
    assert graph.nodes[coord1]["memory_type"] == MemoryType.EPISODIC.value


def test_linking_and_traversal(mem: SomaFractalMemoryEnterprise):
    coord1 = (1, 1, 1)
    coord2 = (2, 2, 2)
    coord3 = (3, 3, 3)
    mem.store_memory(coord1, {"d": 1})
    mem.store_memory(coord2, {"d": 2})
    mem.store_memory(coord3, {"d": 3})

    mem.link_memories(coord1, coord2, "related")
    mem.link_memories(coord2, coord3, "related")

    # Test get_linked_memories
    linked = mem.get_linked_memories(coord1)
    assert len(linked) == 1
    retrieved_coord = linked[0].get("coordinate")
    assert retrieved_coord is not None
    assert tuple(retrieved_coord) == coord2

    # Test find_shortest_path
    path = mem.find_shortest_path(coord1, coord3)
    assert path == [coord1, coord2, coord3]
