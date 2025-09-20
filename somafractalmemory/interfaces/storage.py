from abc import ABC, abstractmethod
from typing import Any, ContextManager, Dict, Iterator, List, Mapping, Optional


class IKeyValueStore(ABC):
    @abstractmethod
    def set(self, key: str, value: bytes):
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def scan_iter(self, pattern: str) -> Iterator[str]:
        pass

    @abstractmethod
    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        pass

    @abstractmethod
    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        pass

    @abstractmethod
    def lock(self, name: str, timeout: int) -> ContextManager:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    # Sorted-set helpers for eviction/indexing
    @abstractmethod
    def zadd(self, key: str, mapping: Mapping[str, float]):
        pass

    @abstractmethod
    def zrange(self, key: str, start: int, end: int, withscores: bool = False):
        pass

    @abstractmethod
    def zrem(self, key: str, *members: str):
        pass

    @abstractmethod
    def zcard(self, key: str) -> int:
        pass

    @abstractmethod
    def zremrangebyrank(self, key: str, start: int, end: int):
        pass


class IVectorStore(ABC):
    @abstractmethod
    def setup(self, vector_dim: int, namespace: str):
        pass

    @abstractmethod
    def upsert(self, points: List[Dict[str, Any]]):
        pass

    @abstractmethod
    def search(self, vector: List[float], top_k: int) -> List[Any]:
        pass

    @abstractmethod
    def delete(self, ids: List[str]):
        pass

    @abstractmethod
    def scroll(self) -> Iterator[Any]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass
