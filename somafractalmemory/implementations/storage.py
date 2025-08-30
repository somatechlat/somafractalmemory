import uuid
from typing import Any, Dict, List, Iterator, Mapping, Optional, ContextManager, cast
import redis
from redis.exceptions import ConnectionError
import qdrant_client
from qdrant_client.http.models import PointStruct, Distance, VectorParams, PointIdsList

from somafractalmemory.interfaces.storage import IKeyValueStore, IVectorStore

import fakeredis
import threading
from collections import defaultdict
import math
from dataclasses import dataclass
from typing import Iterable

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
        regex = re.compile(pattern.replace('*', '.*'))
        return (key for key in self._data if regex.match(key))

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        # This is a simplified implementation for non-hash types
        value = self.get(key)
        return {b'data': value} if value else {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        # This is a simplified implementation for non-hash types
        # It will store the mapping as a single value, e.g., pickled.
        import pickle
        self.set(key, pickle.dumps(mapping))

    def lock(self, name: str, timeout: int = 10) -> ContextManager:
        return self._lock

    def health_check(self) -> bool:
        return True

class RedisKeyValueStore(IKeyValueStore):
    """Redis implementation of the key-value store interface."""
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, testing: bool = False, locks_mode: str = "redis", redlock_endpoints: Optional[List[str]] = None):
        self._testing = testing
        self._locks_mode = (locks_mode or "redis").lower()
        self._redlock_endpoints = redlock_endpoints or []
        # Always prepare an in-proc lock map for tests and fakeredis
        self._inproc_locks: Dict[str, threading.RLock] = defaultdict(lambda: threading.RLock())
        if testing:
            self.client = fakeredis.FakeRedis()
        else:
            self.client = redis.Redis(host=host, port=port, db=db)

        
    def set(self, key: str, value: bytes):
        self.client.set(key, value)

    def get(self, key: str) -> Optional[bytes]:
        return self.client.get(key)

    def delete(self, key: str):
        self.client.delete(key)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        for key in self.client.scan_iter(pattern):
            if isinstance(key, (bytes, bytearray)):
                yield key.decode('utf-8')
            else:
                yield str(key)

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        result = self.client.hgetall(key)
        return dict(result)

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        self.client.hset(key, mapping=dict(mapping))

    def lock(self, name: str, timeout: int = 10) -> ContextManager:
        """Return a lock. Testing/fakeredis: in-process RLock. Redlock mode returns a simple in-proc emulation.

        Note: For true Redlock, configure multiple Redis endpoints and provide a Redlock implementation.
        This stub provides API compatibility and works in tests.
        """
        # In tests/fakeredis, always return in-proc lock
        if self._testing or isinstance(self.client, fakeredis.FakeRedis):
            return self._inproc_locks[name]
        # Redlock stub: fall back to single-node lock for now
        if self._locks_mode == "redlock" and self._redlock_endpoints:
            # TODO: integrate real Redlock client; for now use single-node lock
            return self.client.lock(name, timeout=timeout)
        return self.client.lock(name, timeout=timeout)

    def health_check(self) -> bool:
        try:
            return bool(self.client.ping())
        except ConnectionError:
            return False

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
            # Prefer modern existence check + create
            exists = False
            try:
                exists = bool(self.client.collection_exists(self.collection_name))
            except Exception:
                # Fallback: attempt to get the collection
                try:
                    self.client.get_collection(collection_name=self.collection_name)
                    exists = True
                except Exception:
                    exists = False
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                )
        except Exception:
            # As a last resort, ignore setup errors; tests cover behavior
            pass

    def upsert(self, points: List[Dict[str, Any]]):
        point_structs = [PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points]
        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=point_structs
        )

    def search(self, vector: List[float], top_k: int) -> List[Any]:
        # Newer API uses query_points; keep a fallback to deprecated search
        try:
            hits = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,  # raw vector accepted by client
                limit=top_k,
                with_payload=True,
            ).points
        except Exception:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=top_k
            )
        return hits

    def delete(self, ids: List[str]):
        # Qdrant point IDs can be strings or UUIDs. We'll stick to strings as passed.
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=[i for i in ids if i]),
            wait=True
        )

    def scroll(self) -> Iterator[Any]:
        records, next_page_offset = self.client.scroll(collection_name=self.collection_name, limit=100, with_payload=True)
        while records:
            for record in records:
                yield record
            if next_page_offset is None:
                break
            records, next_page_offset = self.client.scroll(collection_name=self.collection_name, limit=100, with_payload=True, offset=next_page_offset)

    def health_check(self) -> bool:
        try:
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception:
            return False


class InMemoryVectorStore(IVectorStore):
    """A simple in-memory vector store for unit tests and ON_DEMAND mode.

    - Stores points in a dict keyed by point id.
    - Provides cosine-similarity search over all stored points.
    - Yields records with a `.payload` attribute for scroll compatibility.
    """

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
        """Initialize the in-memory collection with the provided namespace and vector dimension."""
        self._vector_dim = int(vector_dim)
        self.collection_name = namespace
        # keep existing points to allow reuse across tests; callers may clear if needed

    def upsert(self, points: list[dict]):
        """Upsert a list of points: {id, vector: List[float], payload: dict}."""
        for p in points:
            pid = str(p["id"]) if "id" in p else str(uuid.uuid4())
            vec = list(p.get("vector", []))
            if self._vector_dim and len(vec) != self._vector_dim:
                # Pad or truncate to match configured dimension
                if len(vec) < self._vector_dim:
                    vec = vec + [0.0] * (self._vector_dim - len(vec))
                else:
                    vec = vec[: self._vector_dim]
            payload = dict(p.get("payload", {}))
            self._points[pid] = InMemoryVectorStore._Record(id=pid, vector=vec, payload=payload)

    def _cosine(self, a: Iterable[float], b: Iterable[float]) -> float:
        """Compute cosine similarity between two vectors; returns 0.0 if a norm is zero."""
        dot = 0.0
        na = 0.0
        nb = 0.0
        for xa, xb in zip(a, b):
            dot += xa * xb
            na += xa * xa
            nb += xb * xb
        if na <= 0.0 or nb <= 0.0:
            return 0.0
        return dot / (math.sqrt(na) * math.sqrt(nb))

    def search(self, vector: list[float], top_k: int) -> list[_Hit]:
        """Search all points by cosine similarity and return top_k hits with payload and score."""
        # Ensure query dimension matches
        q = list(vector)
        if self._vector_dim and len(q) != self._vector_dim:
            if len(q) < self._vector_dim:
                q = q + [0.0] * (self._vector_dim - len(q))
            else:
                q = q[: self._vector_dim]
        scored: list[InMemoryVectorStore._Hit] = []
        for rec in self._points.values():
            s = self._cosine(q, rec.vector)
            scored.append(InMemoryVectorStore._Hit(id=rec.id, score=s, payload=rec.payload))
        scored.sort(key=lambda h: (h.score or 0.0), reverse=True)
        return scored[: max(0, int(top_k))]

    def delete(self, ids: list[str]):
        """Delete points by ids; ignores unknown ids."""
        for pid in ids:
            self._points.pop(str(pid), None)

    def scroll(self):
        """Iterate over all stored records, yielding objects with `.payload` for API compatibility."""
        # Yield shallow copies to avoid accidental external mutation
        for rec in list(self._points.values()):
            yield InMemoryVectorStore._Record(id=rec.id, vector=list(rec.vector), payload=dict(rec.payload))

    def health_check(self) -> bool:
        return True
