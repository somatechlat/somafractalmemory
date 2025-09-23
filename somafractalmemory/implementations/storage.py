"""
Storage implementations for SomaFractalMemory.
"""

# Standard library imports
import inspect
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, ContextManager, Dict, Iterator, List, Mapping, Optional

# Third-party imports
import fakeredis
import qdrant_client
import redis
from qdrant_client.http.models import Distance, PointIdsList, PointStruct, VectorParams
from redis.exceptions import ConnectionError

# Local application imports
from somafractalmemory.interfaces.storage import IKeyValueStore, IVectorStore


# Minimal InMemoryVectorStore for testing
class InMemoryVectorStore(IVectorStore):
    """A simple in-memory vector store for unit tests and ON_DEMAND mode."""

    @dataclass
    class _Record:
        id: str
        vector: list[float]
        payload: dict

    @dataclass
    class _Hit:
        id: str
        score: float | None
        payload: dict

    def __init__(self):
        self._points: dict[str, InMemoryVectorStore._Record] = {}
        self.collection_name: str = ""
        self._vector_dim: int = 0

    def setup(self, vector_dim: int, namespace: str):
        self._vector_dim = int(vector_dim)
        self.collection_name = namespace

    def upsert(self, points: list[dict]):
        for p in points:
            self._points[p["id"]] = InMemoryVectorStore._Record(
                id=p["id"], vector=p["vector"], payload=p.get("payload", {})
            )

    def search(self, vector: list[float], top_k: int) -> list:
        # Return all points as hits for testing
        hits = []
        for rec in self._points.values():
            hits.append(InMemoryVectorStore._Hit(id=rec.id, score=1.0, payload=rec.payload))
        return hits[:top_k]

    def delete(self, ids: list[str]):
        for i in ids:
            self._points.pop(i, None)

    def scroll(self):
        yield from self._points.values()

    def health_check(self) -> bool:
        return True


class InMemoryKeyValueStore(IKeyValueStore):
    """An in-memory implementation of the key-value store for testing and ON_DEMAND mode."""

    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: bytes):
        self._data[key] = value

    def get(self, key: str) -> Optional[bytes]:
        return self._data.get(key)

    def delete(self, key: str):
        if key in self._data:
            del self._data[key]

    def scan_iter(self, pattern: str) -> Iterator[str]:
        # A simple pattern matcher for in-memory store
        import re

        regex = re.compile(pattern.replace("*", ".*"))
        return (key for key in self._data if regex.match(key))

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        # This is a simplified implementation for non-hash types
        value = self.get(key)
        return {b"data": value} if value else {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        # This is a simplified implementation for non-hash types
        # It will store the mapping as a single value using the project's
        # JSON-first serializer to avoid writing binary Python serialized objects to disk.
        from somafractalmemory.serialization import serialize

        try:
            self.set(key, serialize(mapping))
        except Exception:
            # Last-resort fallback to plain str bytes
            self.set(key, str(mapping).encode("utf-8"))

    def lock(self, name: str, timeout: int = 10) -> ContextManager:
        return self._lock

    def health_check(self) -> bool:
        return True


class RedisKeyValueStore(IKeyValueStore):
    def lock(self, name: str, timeout: int = 10):
        if self._testing or isinstance(self.client, fakeredis.FakeRedis):
            return self._inproc_locks[name]
        return self.client.lock(name, timeout=timeout)

    def health_check(self) -> bool:
        try:
            return bool(self.client.ping())
        except ConnectionError:
            return False

    """Redis implementation of the key-value store interface."""

    def __init__(
        self, host: str = "localhost", port: int = 6379, db: int = 0, testing: bool = False
    ):
        self._testing = testing
        # Always prepare an in-proc lock map for tests and fakeredis
        self._inproc_locks: Dict[str, threading.RLock] = defaultdict(lambda: threading.RLock())
        if testing:
            self.client = fakeredis.FakeRedis()
        else:
            self.client = redis.Redis(host=host, port=port, db=db)

    def set(self, key: str, value: bytes):
        self.client.set(key, value)

    def get(self, key: str) -> Optional[bytes]:
        result = self.client.get(key)
        if inspect.isawaitable(result):
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(result)
        if isinstance(result, (bytes, type(None))):
            return result
        return None

    def delete(self, key: str):
        self.client.delete(key)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        for key in self.client.scan_iter(pattern):
            if isinstance(key, (bytes, bytearray)):
                yield key.decode("utf-8")
            else:
                yield str(key)

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        result = self.client.hgetall(key)
        if inspect.isawaitable(result):
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(result)
        if isinstance(result, dict):
            return {
                k: v for k, v in result.items() if isinstance(k, bytes) and isinstance(v, bytes)
            }
        return {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        self.client.hset(key, mapping=dict(mapping))


class QdrantVectorStore(IVectorStore):
    """Qdrant implementation of the vector store interface."""

    def __init__(self, collection_name: str, **kwargs):
        self._init_kwargs = kwargs
        self.client = qdrant_client.QdrantClient(**self._init_kwargs)
        self.collection_name = collection_name

    @property
    def is_on_disk(self) -> bool:
        """Checks if the Qdrant client is using on-disk storage."""
        if "url" in self._init_kwargs or "host" in self._init_kwargs:
            return False  # It's a remote client
        path = self._init_kwargs.get("path")
        location = self._init_kwargs.get("location")
        return path is not None and path != ":memory:" and location != ":memory:"

    def setup(self, vector_dim: int, namespace: str):
        self.collection_name = namespace
        try:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
            )
        except Exception:  # Catch if collection already exists
            pass

    def upsert(self, points: List[Dict[str, Any]]):
        point_structs = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points
        ]
        self.client.upsert(collection_name=self.collection_name, wait=True, points=point_structs)

    def search(self, vector: List[float], top_k: int) -> List[Any]:
        hits = self.client.search(
            collection_name=self.collection_name, query_vector=vector, limit=top_k
        )
        return hits

    def delete(self, ids: List[str]):
        # Qdrant point IDs can be strings or UUIDs. We'll stick to strings as passed.
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=[i for i in ids if i]),
            wait=True,
        )

    def scroll(self) -> Iterator[Any]:
        records, next_page_offset = self.client.scroll(
            collection_name=self.collection_name, limit=100, with_payload=True
        )
        while records:
            yield from records
            if next_page_offset is None:
                break
            records, next_page_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                with_payload=True,
                offset=next_page_offset,
            )

    def health_check(self) -> bool:
        try:
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception:
            return False
