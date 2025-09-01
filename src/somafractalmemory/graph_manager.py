# graph_manager.py - Handles semantic graph operations

from typing import Dict, Any, List, Tuple, Optional
import logging

from .interfaces.graph import IGraphStore

logger = logging.getLogger(__name__)

class GraphManager:
    def __init__(self, graph_store: IGraphStore) -> None:
        self.graph_store = graph_store

    def add_memory(self, coordinate: Tuple[float, ...], value: Dict[str, Any]) -> None:
        self.graph_store.add_memory(coordinate, value)

    def remove_memory(self, coordinate: Tuple[float, ...]) -> None:
        self.graph_store.remove_memory(coordinate)

    def add_link(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_data: Dict[str, Any]) -> None:
        self.graph_store.add_link(from_coord, to_coord, link_data)

    def get_neighbors(self, coord: Tuple[float, ...], link_type: Optional[str] = None, limit: Optional[int] = None) -> List[Tuple[Tuple[float, ...], Dict[str, Any]]]:
        return self.graph_store.get_neighbors(coord, link_type=link_type, limit=limit)

    def find_shortest_path(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_type: Optional[str] = None) -> List[Tuple[float, ...]]:
        return self.graph_store.find_shortest_path(from_coord, to_coord, link_type)

    def export_graph(self, path: str = "semantic_graph.graphml") -> None:
        self.graph_store.export_graph(path)

    def import_graph(self, path: str = "semantic_graph.graphml") -> None:
        self.graph_store.import_graph(path)

    def clear(self) -> None:
        self.graph_store.clear()

    def sync_from_memories(self, memories: List[Dict[str, Any]]) -> None:
        self.clear()
        for mem in memories:
            coord_val = mem.get("coordinate")
            if coord_val is not None:
                coord = tuple(coord_val)
                self.add_memory(coord, mem)
