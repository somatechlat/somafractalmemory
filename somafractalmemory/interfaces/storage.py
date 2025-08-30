from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Iterator, Mapping, Optional, ContextManager

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
