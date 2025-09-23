"""
Storage implementations for SomaFractalMemory.
"""

# Standard library imports
import inspect
import json
import os
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, ContextManager, Dict, Iterator, List, Mapping, Optional

# Third‑party imports (alphabetical)
import fakeredis
import psycopg2
import qdrant_client
import redis

# Optional OpenTelemetry instrumentation imports – may be unavailable in minimal environments.
try:
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
except Exception:  # pragma: no cover

    class Psycopg2Instrumentor:  # type: ignore
        @staticmethod
        def instrument() -> None:
            """No‑op fallback when OpenTelemetry is not installed."""
            return None


try:
    from opentelemetry.instrumentation.qdrant import QdrantInstrumentor
except Exception:  # pragma: no cover

    class QdrantInstrumentor:  # type: ignore
        @staticmethod
        def instrument() -> None:
            """No‑op fallback when OpenTelemetry is not installed."""
            return None


# Specific third‑party imports
from psycopg2.extras import Json
from qdrant_client.http.models import Distance, PointIdsList, PointStruct, VectorParams
from redis.exceptions import ConnectionError

# Local application imports
from somafractalmemory.interfaces.storage import IKeyValueStore, IVectorStore

# Initialise instrumentation (executed at import time). These calls are safe even if the
# instrumentors are the no‑op stubs defined above.
Psycopg2Instrumentor().instrument()
QdrantInstrumentor().instrument()


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


# Hybrid KV store for DEVELOPMENT mode: primary persistence in Postgres with optional Redis caching.
class PostgresRedisHybridStore(IKeyValueStore):
    """Combine a PostgresKeyValueStore (canonical) with a RedisKeyValueStore.

    * ``set`` writes to both stores.
    * ``get`` tries Redis first (cache hit) and falls back to Postgres.
    * ``delete`` removes from both.
    * ``scan_iter`` merges keys from both stores, deduplicating.
    * ``hgetall`` / ``hset`` prefer Postgres, but also keep Redis in sync.
    * ``lock`` uses Redis if available, otherwise falls back to the Postgres store's simple in‑process lock.
    * ``health_check`` requires both backends to be healthy.
    """

    def __init__(
        self, pg_store: "PostgresKeyValueStore", redis_store: Optional["RedisKeyValueStore"] = None
    ):
        self.pg_store = pg_store
        self.redis_store = redis_store

    # ----- Basic KV operations -----
    def set(self, key: str, value: bytes):
        self.pg_store.set(key, value)
        if self.redis_store:
            self.redis_store.set(key, value)

    def get(self, key: str) -> Optional[bytes]:
        if self.redis_store:
            cached = self.redis_store.get(key)
            if cached is not None:
                return cached
        return self.pg_store.get(key)

    def delete(self, key: str):
        self.pg_store.delete(key)
        if self.redis_store:
            self.redis_store.delete(key)

    # ----- Iteration & hash helpers -----
    def scan_iter(self, pattern: str) -> Iterator[str]:
        seen: set[str] = set()
        for k in self.pg_store.scan_iter(pattern):
            seen.add(k)
            yield k
        if self.redis_store:
            for k in self.redis_store.scan_iter(pattern):
                if k not in seen:
                    seen.add(k)
                    yield k

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        pg_val = self.pg_store.hgetall(key)
        if pg_val:
            return pg_val
        if self.redis_store:
            return self.redis_store.hgetall(key)
        return {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        self.pg_store.hset(key, mapping)
        if self.redis_store:
            self.redis_store.hset(key, mapping)

    # ----- Lock & health -----
    def lock(self, name: str, timeout: int = 10):
        if self.redis_store:
            return self.redis_store.lock(name, timeout)
        return self.pg_store.lock(name, timeout)

    def health_check(self) -> bool:
        ok = self.pg_store.health_check()
        if self.redis_store:
            ok = ok and self.redis_store.health_check()
        return ok


class QdrantVectorStore(IVectorStore):
    """Qdrant implementation of the vector store interface."""

    def __init__(self, collection_name: str, **kwargs):
        self._init_kwargs = kwargs
        # TLS/SSL configuration – optional env vars
        self._use_tls = os.getenv("QDRANT_TLS", "false").lower() == "true"
        self._cert_path = os.getenv("QDRANT_TLS_CERT")
        # If TLS is requested, ensure the client uses https scheme
        if self._use_tls:
            url = self._init_kwargs.get("url")
            if url and not url.startswith("https://"):
                # Remove the http:// prefix safely and prepend https://
                self._init_kwargs["url"] = f"https://{url.removeprefix('http://')}"
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


# Postgres-backed key-value store (canonical storage for EVENTED_ENTERPRISE)


class PostgresKeyValueStore(IKeyValueStore):
    """Simple Postgres implementation of IKeyValueStore.

    Stores arbitrary keys with JSONB values in a table ``kv_store``.
    The table is created on first use if it does not exist.
    """

    _TABLE_NAME = "kv_store"

    def __init__(self, url: str | None = None):
        # testcontainers may provide a SQLAlchemy‑style URL like
        # ``postgresql+psycopg2://user:pass@host:port/db`` which psycopg2 does not
        # understand. Convert it to the libpq format (``postgresql://``) before
        # passing it to ``psycopg2.connect``.
        raw_url = url or os.getenv("POSTGRES_URL", "postgresql://soma:soma@localhost:5432/soma")
        # Strip the ``+psycopg2`` dialect suffix if present.
        self._url = raw_url.replace("postgresql+psycopg2://", "postgresql://", 1)
        # TLS/SSL configuration – optional env vars
        self._sslmode = os.getenv("POSTGRES_SSL_MODE")  # e.g. "require"
        self._sslrootcert = os.getenv("POSTGRES_SSL_ROOT_CERT")
        self._sslcert = os.getenv("POSTGRES_SSL_CERT")
        self._sslkey = os.getenv("POSTGRES_SSL_KEY")
        self._conn = None
        self._lock = threading.RLock()
        self._ensure_connection()
        self._ensure_table()

    def _ensure_connection(self):
        if self._conn is None:
            conn_kwargs = {}
            if self._sslmode:
                conn_kwargs["sslmode"] = self._sslmode
            if self._sslrootcert:
                conn_kwargs["sslrootcert"] = self._sslrootcert
            if self._sslcert:
                conn_kwargs["sslcert"] = self._sslcert
            if self._sslkey:
                conn_kwargs["sslkey"] = self._sslkey
            self._conn = psycopg2.connect(self._url, **conn_kwargs)
            self._conn.autocommit = True

    def _ensure_table(self):
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._TABLE_NAME} (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL
                );
                """
            )

    def set(self, key: str, value: bytes):
        # value is expected to be JSON-encoded bytes
        try:
            json_obj = json.loads(value)
        except Exception:
            # Fallback: store as plain string
            json_obj = value.decode("utf-8", errors="ignore")
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self._TABLE_NAME} (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
                """,
                (key, Json(json_obj)),
            )

    def get(self, key: str) -> Optional[bytes]:
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT value FROM {self._TABLE_NAME} WHERE key = %s;", (key,))
            row = cur.fetchone()
            if row:
                # row[0] is a Python dict (psycopg2 converts JSONB to dict)
                return json.dumps(row[0]).encode("utf-8")
            return None

    def delete(self, key: str):
        with self._conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._TABLE_NAME} WHERE key = %s;", (key,))

    def scan_iter(self, pattern: str) -> Iterator[str]:
        # Convert glob pattern * to SQL %
        sql_pattern = pattern.replace("*", "%")
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT key FROM {self._TABLE_NAME} WHERE key LIKE %s;", (sql_pattern,))
            for (k,) in cur.fetchall():
                yield k

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        # Not used in core for canonical store; return empty dict.
        return {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        # Store mapping as JSON under the key (overwrites existing value).
        try:
            json_obj = {k.decode(): json.loads(v) for k, v in mapping.items()}
        except Exception:
            json_obj = {k.decode(): v.decode() for k, v in mapping.items()}
        self.set(key, json.dumps(json_obj).encode("utf-8"))

    def lock(self, name: str, timeout: int = 10) -> ContextManager:
        return self._lock

    def health_check(self) -> bool:
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return True
        except Exception:
            return False
