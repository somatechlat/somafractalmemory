from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from somafractalmemory.interfaces.graph import IGraphStore


class NetworkXGraphStore(IGraphStore):
    """NetworkX implementation of the graph store interface."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_memory(self, coordinate: Tuple[float, ...], memory_data: Dict[str, Any]):
        self.graph.add_node(coordinate, **memory_data)

    def add_link(
        self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_data: Dict[str, Any]
    ):
        self.graph.add_edge(from_coord, to_coord, **link_data)

    def get_neighbors(
        self,
        coordinate: Tuple[float, ...],
        link_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Tuple[Any, Dict[str, Any]]]:
        neighbors: List[Tuple[Any, Dict[str, Any]]] = []
        for neighbor in self.graph.neighbors(coordinate):
            edge_data = self.graph.get_edge_data(coordinate, neighbor)
            if link_type is None or edge_data.get("type") == link_type:
                neighbors.append((neighbor, edge_data))
        if limit is not None:
            neighbors = neighbors[: max(0, int(limit))]
        return neighbors

    def find_shortest_path(
        self,
        from_coord: Tuple[float, ...],
        to_coord: Tuple[float, ...],
        link_type: Optional[str] = None,
    ) -> List[Any]:
        # If link_type specified, filter edges to those with matching 'type'
        G = self.graph
        if link_type is not None:
            # Create a subgraph view with only edges of the specified type
            def edge_filter(u, v):
                data = G.get_edge_data(u, v)
                return data.get("type") == link_type

            # Build a DiGraph of allowed edges
            H = nx.DiGraph()
            H.add_nodes_from(G.nodes(data=True))
            for u, v, data in G.edges(data=True):
                if data.get("type") == link_type:
                    H.add_edge(u, v, **data)
            G = H
        try:
            # Use weighted shortest path if 'weight' attribute exists; falls back to 1 otherwise
            return list(nx.shortest_path(G, source=from_coord, target=to_coord, weight="weight"))
        except nx.NetworkXNoPath:
            return []

    def remove_memory(self, coordinate: Tuple[float, ...]):
        if self.graph.has_node(coordinate):
            self.graph.remove_node(coordinate)

    def clear(self):
        self.graph.clear()

    def export_graph(self, path: str):
        nx.write_graphml(self.graph, path)

    def import_graph(self, path: str):
        self.graph = nx.read_graphml(path)

    def health_check(self) -> bool:
        # The graph is in-memory, so it's always "healthy" if the object exists.
        return True
