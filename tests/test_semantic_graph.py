import pytest
import networkx as nx
from somafractalmemory.core import SomaFractalMemoryEnterprise, MemoryType
import numpy as np

def test_semantic_graph_basic():
    mem = SomaFractalMemoryEnterprise(namespace="test_graph", redis_nodes=[{"host": "localhost", "port": 6379}])
    # Store two memories and link them
    coord1 = (1.0, 2.0)
    coord2 = (3.0, 4.0)
    mem.store_memory(coord1, {"task": "A", "coordinate": coord1}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(coord2, {"task": "B", "coordinate": coord2}, memory_type=MemoryType.EPISODIC)
    mem.link_memories(coord1, coord2, link_type="related")
    # Graph should have two nodes and one edge
    assert mem.graph.has_node(coord1)
    assert mem.graph.has_node(coord2)
    assert mem.graph.has_edge(coord1, coord2)
    # Test neighbor retrieval
    neighbors = mem.get_neighbors(coord1)
    assert any(n[0] == coord2 for n in neighbors)
    # Test shortest path
    path = mem.find_shortest_path(coord1, coord2)
    assert path == [coord1, coord2]

def test_semantic_graph_export_import(tmp_path):
    mem = SomaFractalMemoryEnterprise(namespace="test_graph2", redis_nodes=[{"host": "localhost", "port": 6379}])
    coord1 = (5.0, 6.0)
    coord2 = (7.0, 8.0)
    mem.store_memory(coord1, {"task": "C", "coordinate": coord1}, memory_type=MemoryType.EPISODIC)
    mem.store_memory(coord2, {"task": "D", "coordinate": coord2}, memory_type=MemoryType.EPISODIC)
    mem.link_memories(coord1, coord2, link_type="cause")
    export_path = tmp_path / "graph.graphml"
    mem.export_graph(str(export_path))
    # Create a new instance and import
    mem2 = SomaFractalMemoryEnterprise(namespace="test_graph3", redis_nodes=[{"host": "localhost", "port": 6379}])
    mem2.import_graph(str(export_path))
    assert mem2.graph.has_node(coord1)
    assert mem2.graph.has_node(coord2)
    assert mem2.graph.has_edge(coord1, coord2)
    edge_data = mem2.graph.get_edge_data(coord1, coord2)
    assert edge_data.get("type") == "cause"
