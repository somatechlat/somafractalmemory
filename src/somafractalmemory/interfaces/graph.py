from abc import ABC, abstractmethod
from typing import Any


class IGraphStore(ABC):
    @abstractmethod
    def add_memory(self, coordinate: tuple[float, ...], memory_data: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def add_link(
        self, from_coord: tuple[float, ...], to_coord: tuple[float, ...], link_data: dict[str, Any]
    ) -> None:
        pass

    @abstractmethod
    def get_neighbors(
        self,
        coordinate: tuple[float, ...],
        link_type: str | None = None,
        limit: int | None = None,
    ) -> list[tuple[Any, dict[str, Any]]]:
        pass

    @abstractmethod
    def find_shortest_path(
        self,
        from_coord: tuple[float, ...],
        to_coord: tuple[float, ...],
        link_type: str | None = None,
    ) -> list[Any]:
        pass

    @abstractmethod
    def remove_memory(self, coordinate: tuple[float, ...]) -> None:
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
