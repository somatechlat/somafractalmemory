from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager
from typing import Any


class IKeyValueStore(ABC):
    @abstractmethod
    def set(self, key: str, value: bytes):
        pass

    @abstractmethod
    def get(self, key: str) -> bytes | None:
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def scan_iter(self, pattern: str) -> Iterator[str]:
        pass

    @abstractmethod
    def hgetall(self, key: str) -> dict[bytes, bytes]:
        pass

    @abstractmethod
    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        pass

    @abstractmethod
    def lock(self, name: str, timeout: int) -> AbstractContextManager:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass


class IVectorStore(ABC):
    @abstractmethod
    def setup(self, vector_dim: int, namespace: str):
        pass

    @abstractmethod
    def upsert(self, points: list[dict[str, Any]]):
        pass

    @abstractmethod
    def search(self, vector: list[float], top_k: int) -> list[Any]:
        pass

    @abstractmethod
    def delete(self, ids: list[str]):
        pass

    @abstractmethod
    def scroll(self) -> Iterator[Any]:
        pass

    @abstractmethod
    def count(self) -> int:
        """Return the number of entities in the collection."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass
