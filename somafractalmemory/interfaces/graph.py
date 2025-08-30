from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Dict, Optional

class IGraphStore(ABC):
    @abstractmethod
    def add_memory(self, coordinate: Tuple[float, ...], memory_data: Dict[str, Any]):
        pass

    @abstractmethod
    def add_link(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_data: Dict[str, Any]):
        pass

    @abstractmethod
    def get_neighbors(self, coordinate: Tuple[float, ...], link_type: Optional[str] = None, limit: Optional[int] = None) -> List[Tuple[Any, Dict[str, Any]]]:
        pass

    @abstractmethod
    def find_shortest_path(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_type: Optional[str] = None) -> List[Any]:
        pass

    @abstractmethod
    def remove_memory(self, coordinate: Tuple[float, ...]):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def export_graph(self, path: str):
        pass

    @abstractmethod
    def import_graph(self, path: str):
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass
