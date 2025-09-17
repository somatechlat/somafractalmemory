from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class IGraphStore(ABC):
    @abstractmethod
    def add_memory(self, coordinate: Tuple[float, ...], memory_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def add_link(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_neighbors(self, coordinate: Tuple[float, ...], link_type: Optional[str] = None, limit: Optional[int] = None) -> List[Tuple[Any, Dict[str, Any]]]:
        pass

    @abstractmethod
    def find_shortest_path(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_type: Optional[str] = None) -> List[Any]:
        pass

    @abstractmethod
    def remove_memory(self, coordinate: Tuple[float, ...]) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def export_graph(self, path: str) -> None:
        pass

    @abstractmethod
    def import_graph(self, path: str) -> None:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass
