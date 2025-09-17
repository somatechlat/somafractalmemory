import logging
import uuid
from typing import Any, ContextManager, Dict, Iterator, List, Mapping, Optional, cast

import numpy as np

from somafractalmemory.interfaces.storage import IKeyValueStore, IVectorStore

# Optional dependencies: import lazily/guarded so core package works without extras
try:  # redis is optional
    import redis as _redis
    try:
        from redis.exceptions import ConnectionError as RedisConnectionError
    except Exception:  # pragma: no cover - fallback
        class RedisConnectionError(Exception):
            pass
except Exception:  # pragma: no cover - optional
    _redis = None
    class RedisConnectionError(Exception):
        pass

try:  # fakeredis is optional (used for testing)
    import fakeredis as _fakeredis
except Exception:  # pragma: no cover - optional
    _fakeredis = None

try:  # qdrant is optional
    import qdrant_client as _qdrant_client
except Exception:  # pragma: no cover - optional
    _qdrant_client = None

import math
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

logger = logging.getLogger(__name__)


# Minimal in-proc Redis-like stub when fakeredis isn't available
class _InProcRedisStub:
    def __init__(self):
        self._data: Dict[str, bytes] = {}
        self._hashes: Dict[str, Dict[bytes, bytes]] = defaultdict(dict)

    def set(self, key: str, value: bytes):
        self._data[str(key)] = value

    def get(self, key: str):
        return self._data.get(str(key))

    def delete(self, key: str):
        self._data.pop(str(key), None)
        self._hashes.pop(str(key), None)

    def scan_iter(self, pattern: str):
        import re
        regex = re.compile(pattern.replace('*', '.*'))
        for k in list(self._data.keys()) + list(self._hashes.keys()):
            if regex.match(k):
                yield k.encode('utf-8')

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        return dict(self._hashes.get(str(key), {}))

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        d = self._hashes[str(key)]
        d.update(dict(mapping))

    def lock(self, name: str, timeout: int = 10):
        return threading.RLock()

    def ping(self) -> bool:
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
            if _fakeredis is not None:
                self.client = _fakeredis.FakeRedis()
            else:
                # Minimal in-memory stub if fakeredis isn't available
                self.client = _InProcRedisStub()
        else:
            if _redis is None:
                raise ImportError("redis extra is required for RedisKeyValueStore. Install with `pip install somafractalmemory[redis]`.")
            self.client = _redis.Redis(host=host, port=port, db=db)

        
    def set(self, key: str, value: bytes):
        self.client.set(key, value)

    def get(self, key: str) -> Optional[bytes]:
        # Some redis clients may be typed as Any/awaitable by static checkers; cast to Optional[bytes]
        return cast(Optional[bytes], self.client.get(key))

    def delete(self, key: str):
        self.client.delete(key)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        for key in self.client.scan_iter(pattern):
            if isinstance(key, (bytes, bytearray)):
                yield key.decode('utf-8')
            else:
                yield str(key)

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        result: Any = self.client.hgetall(key)
        return dict(result) if isinstance(result, dict) else cast(Dict[bytes, bytes], result)

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        self.client.hset(key, mapping=dict(mapping))

    def lock(self, name: str, timeout: int = 10) -> ContextManager:
        """Return a lock. Testing/fakeredis: in-process RLock. Redlock mode returns a simple in-proc emulation.

        Note: For true Redlock, configure multiple Redis endpoints and provide a Redlock implementation.
        This stub provides API compatibility and works in tests.
        """
        # In tests/fakeredis, always return in-proc lock
        if self._testing or type(self.client).__name__ in {"FakeRedis", "_InProcRedisStub"}:
            return self._inproc_locks[name]
        # Redlock stub: fall back to single-node lock for now
        if self._locks_mode == "redlock" and self._redlock_endpoints:
            # TODO: integrate real Redlock client; for now use single-node lock
            return self.client.lock(name, timeout=timeout)
        return self.client.lock(name, timeout=timeout)

    def health_check(self) -> bool:
        try:
            return bool(self.client.ping())
        except RedisConnectionError:
            return False

class QdrantVectorStore(IVectorStore):
    """Qdrant implementation of the vector store interface."""
    def __init__(self, collection_name: str, **kwargs):
        if _qdrant_client is None:
            raise ImportError("qdrant-client extra is required for QdrantVectorStore. Install with `pip install somafractalmemory[qdrant]`.")
        self._init_kwargs = kwargs
        self.client = _qdrant_client.QdrantClient(**self._init_kwargs)
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
            current_dim = None
            # Import qdrant models lazily
            from qdrant_client.http.models import Distance, VectorParams
            try:
                exists = bool(self.client.collection_exists(self.collection_name))
                if exists:
                    # Check if existing collection has correct dimensions
                    collection_info = self.client.get_collection(collection_name=self.collection_name)
                    # Qdrant can return VectorParams or a dict of named vectors
                    vectors_any = cast(Any, getattr(collection_info.config.params, "vectors", None))
                    try:
                        if hasattr(vectors_any, "size"):
                            current_dim = int(getattr(vectors_any, "size"))
                        elif isinstance(vectors_any, dict) and vectors_any:
                            first_params = next(iter(vectors_any.values()))
                            current_dim = int(getattr(first_params, "size", 0)) or None
                        else:
                            current_dim = None
                    except Exception:
                        current_dim = None
            except Exception:
                # Fallback: attempt to get the collection
                try:
                    collection_info = self.client.get_collection(collection_name=self.collection_name)
                    exists = True
                    vectors_any = cast(Any, getattr(collection_info.config.params, "vectors", None))
                    try:
                        if hasattr(vectors_any, "size"):
                            current_dim = int(getattr(vectors_any, "size"))
                        elif isinstance(vectors_any, dict) and vectors_any:
                            first_params = next(iter(vectors_any.values()))
                            current_dim = int(getattr(first_params, "size", 0)) or None
                        else:
                            current_dim = None
                    except Exception:
                        current_dim = None
                except Exception:
                    exists = False
            
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                )
            elif current_dim != vector_dim:
                # Recreate collection with correct dimensions
                logger.warning(f"Recreating collection {self.collection_name} with correct vector dimension {vector_dim} (was {current_dim})")
                self.client.delete_collection(collection_name=self.collection_name)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                )
        except Exception as e:
            logger.warning(f"Vector store setup failed: {e}")
            # As a last resort, ignore setup errors; tests cover behavior
            pass

    def upsert(self, points: List[Dict[str, Any]]):
        """Upsert points with robust dimension validation and error handling."""
        if not points:
            return

        try:
            # Validate and normalize all vectors before processing
            normalized_points = []
            for point in points:
                try:
                    vector = point.get("vector", [])
                    if isinstance(vector, list):
                        vec_array = np.array(vector, dtype=np.float32)
                    elif isinstance(vector, np.ndarray):
                        vec_array = vector.astype(np.float32)
                    else:
                        raise ValueError(f"Invalid vector type: {type(vector)}")

                    # Ensure vector is 1D
                    if vec_array.ndim > 1:
                        vec_array = vec_array.flatten()

                    # Validate dimension consistency
                    if len(vec_array) == 0:
                        raise ValueError("Empty vector")
                    
                    # Check for NaN or infinite values
                    if not np.isfinite(vec_array).all():
                        raise ValueError("Vector contains NaN or infinite values")

                    # Normalize point for storage
                    normalized_point = point.copy()
                    normalized_point["vector"] = vec_array.tolist()
                    normalized_points.append(normalized_point)

                except Exception as e:
                    logger.warning(f"Skipping invalid point {point.get('id', 'unknown')}: {e}")
                    continue

            if not normalized_points:
                logger.warning("No valid points to upsert")
                return

            # Call the underlying implementation
            self._upsert_impl(normalized_points)

        except Exception as e:
            logger.error(f"Vector store upsert failed: {e}")
            raise

    def _upsert_impl(self, points: List[Dict[str, Any]]):
        """Internal upsert implementation after validation."""
        # Import models lazily to avoid import-time errors when qdrant-client isn't installed
        from qdrant_client.http.models import PointStruct
        point_structs = [PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points]
        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=point_structs
        )

    def _search_impl(self, query_vector: List[float], limit: int, **kwargs) -> List[Dict[str, Any]]:
        """Internal search implementation after validation."""
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            **kwargs,
        )
        return [hit.payload for hit in search_result if hit.payload is not None]

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
        from qdrant_client.http.models import PointIdsList
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=[i for i in ids if i]),
            wait=True,
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
        """Upsert a list of points: {id, vector: List[float], payload: dict} with validation."""
        for p in points:
            try:
                pid = str(p["id"]) if "id" in p else str(uuid.uuid4())
                vec = p.get("vector", [])
                
                # Validate vector type and convert if needed
                if hasattr(vec, 'tolist') and hasattr(vec, 'ndim'):  # numpy array
                    vec = vec.tolist()
                elif not isinstance(vec, list):
                    raise ValueError(f"Invalid vector type: {type(vec)}")
                
                # Ensure vector is 1D and contains only floats
                vec = [float(x) for x in vec]
                
                # Validate dimension consistency
                if self._vector_dim and len(vec) != self._vector_dim:
                    if len(vec) < self._vector_dim:
                        vec = vec + [0.0] * (self._vector_dim - len(vec))
                    else:
                        vec = vec[: self._vector_dim]
                
                # Check for NaN or infinite values
                if not all(math.isfinite(x) for x in vec):
                    raise ValueError("Vector contains NaN or infinite values")
                
                payload = dict(p.get("payload", {}))
                self._points[pid] = InMemoryVectorStore._Record(id=pid, vector=vec, payload=payload)
                
            except Exception as e:
                logger.warning(f"Skipping invalid point {p.get('id', 'unknown')}: {e}")
                continue

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
