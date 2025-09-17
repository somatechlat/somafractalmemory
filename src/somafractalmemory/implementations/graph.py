import threading
from typing import Any

import networkx as nx

from somafractalmemory.interfaces.graph import IGraphStore


class NetworkXGraphStore(IGraphStore):
    """NetworkX implementation of the graph store interface with thread safety."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self._lock = threading.RLock()  # Reentrant lock for thread safety

    def add_memory(self, coordinate: tuple[float, ...], memory_data: dict[str, Any]) -> None:
        with self._lock:
            self.graph.add_node(coordinate, **memory_data)

    def add_link(
        self, from_coord: tuple[float, ...], to_coord: tuple[float, ...], link_data: dict[str, Any]
    ) -> None:
        with self._lock:
            self.graph.add_edge(from_coord, to_coord, **link_data)

    def get_neighbors(
        self,
        coordinate: tuple[float, ...],
        link_type: str | None = None,
        limit: int | None = None,
    ) -> list[tuple[Any, dict[str, Any]]]:
        with self._lock:
            neighbors: list[tuple[Any, dict[str, Any]]] = []
            for neighbor in self.graph.neighbors(coordinate):
                raw_edge_data = self.graph.get_edge_data(coordinate, neighbor) or {}
                edge_data: dict[str, Any] = dict(raw_edge_data)
                if link_type is None or edge_data.get("type") == link_type:
                    neighbors.append((neighbor, edge_data))
            if limit is not None:
                neighbors = neighbors[: max(0, int(limit))]
            return neighbors

    def find_shortest_path(
        self,
        from_coord: tuple[float, ...],
        to_coord: tuple[float, ...],
        link_type: str | None = None,
    ) -> list[Any]:
        with self._lock:
            if link_type is not None:
                # Use a memory-efficient subgraph view
                view = nx.subgraph_view(
                    self.graph,
                    filter_edge=lambda u, v: self.graph.get_edge_data(u, v).get("type")
                    == link_type,
                )
                G = view
            else:
                G = self.graph

            # Ensure both source and target nodes exist in the graph view
            if from_coord not in G or to_coord not in G:
                return []

            try:
                # Use weighted shortest path if 'weight' attribute exists; falls back to 1 otherwise
                return list(
                    nx.shortest_path(G, source=from_coord, target=to_coord, weight="weight")
                )
            except nx.NetworkXNoPath:
                return []

    def remove_memory(self, coordinate: tuple[float, ...]) -> None:
        with self._lock:
            if self.graph.has_node(coordinate):
                self.graph.remove_node(coordinate)

    def clear(self) -> None:
        with self._lock:
            self.graph.clear()

    def export_graph(self, path: str) -> None:
        with self._lock:
            nx.write_graphml(self.graph, path)

    def import_graph(self, path: str) -> None:
        with self._lock:
            self.graph = nx.read_graphml(path)

    def health_check(self) -> bool:
        with self._lock:
            # The graph is in-memory, so it's always "healthy" if the object exists.
            return True
