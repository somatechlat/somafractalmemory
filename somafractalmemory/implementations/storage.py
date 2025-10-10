"""
Storage implementations for SomaFractalMemory.
"""

# Standard library imports
import inspect
import json
import os
import threading
from collections import defaultdict
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Optional

# Third‑party imports (alphabetical)
import psycopg2
import qdrant_client
import redis
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

# Specific third‑party imports
from psycopg2.extras import Json
from psycopg2.sql import SQL, Identifier
from qdrant_client.http.models import Distance, PointIdsList, PointStruct, VectorParams
from redis.exceptions import ConnectionError

# Local application imports
from somafractalmemory.interfaces.storage import IKeyValueStore, IVectorStore

# Initialise instrumentation (executed at import time). These calls are safe even if the
# instrumentors are the no‑op stubs defined above.
Psycopg2Instrumentor().instrument()


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
            vec = p["vector"]
            # Ensure vector dimensionality & normalization (L2) – defensive; skip heavy ops if already unit.
            if self._vector_dim and len(vec) == self._vector_dim:
                import math

                norm = math.sqrt(sum(x * x for x in vec)) or 1.0
                vec = [x / norm for x in vec]
            rec = InMemoryVectorStore._Record(id=p["id"], vector=vec, payload=p.get("payload", {}))
            self._points[p["id"]] = rec

    def search(self, vector: list[float], top_k: int) -> list:
        # Real cosine similarity (vectors assumed normalized; normalize query defensively)
        import math

        q_norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        q = [x / q_norm for x in vector]
        hits: list[InMemoryVectorStore._Hit] = []
        for rec in self._points.values():
            # Dot product (both normalized) gives cosine
            sim = sum(a * b for a, b in zip(rec.vector, q, strict=True))
            if sim < 0:
                sim = 0.0  # clamp negative similarity
            imp = rec.payload.get("importance_norm")
            if isinstance(imp, int | float):
                sim *= float(imp)
            hits.append(InMemoryVectorStore._Hit(id=rec.id, score=sim, payload=rec.payload))
        # Partial selection for small in-memory test set: full sort acceptable
        hits.sort(key=lambda h: (h.score if h.score is not None else -1.0), reverse=True)
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

    def get(self, key: str) -> bytes | None:
        return self._data.get(key)

    def delete(self, key: str):
        if key in self._data:
            del self._data[key]

    def scan_iter(self, pattern: str) -> Iterator[str]:
        # A simple pattern matcher for in-memory store
        import re

        regex = re.compile(pattern.replace("*", ".*"))
        return (key for key in self._data if regex.match(key))

    def hgetall(self, key: str) -> dict[bytes, bytes]:
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

    def lock(self, name: str, timeout: int = 10) -> AbstractContextManager:
        return self._lock

    def health_check(self) -> bool:
        return True


class RedisKeyValueStore(IKeyValueStore):
    def lock(self, name: str, timeout: int = 10) -> AbstractContextManager:
        if self._testing:
            # Testing mode unsupported in no-mock deployments
            raise RuntimeError("Testing mode is unsupported: use a real Redis instance")
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
        self._inproc_locks: dict[str, threading.RLock] = defaultdict(lambda: threading.RLock())
        if testing:
            raise RuntimeError(
                "Testing mode with in-memory fakeredis is not supported in this deployment. Use a real Redis server."
            )
        self.client = redis.Redis(host=host, port=port, db=db)

    def set(self, key: str, value: bytes):
        self.client.set(key, value)

    def get(self, key: str) -> bytes | None:
        result = self.client.get(key)
        if inspect.isawaitable(result):
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(result)
        if isinstance(result, bytes | type(None)):
            return result
        return None

    def delete(self, key: str):
        self.client.delete(key)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        for key in self.client.scan_iter(pattern):
            if isinstance(key, bytes | bytearray):
                yield key.decode("utf-8")
            else:
                yield str(key)

    def hgetall(self, key: str) -> dict[bytes, bytes]:
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

    def get(self, key: str) -> bytes | None:
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

    def hgetall(self, key: str) -> dict[bytes, bytes]:
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
    def lock(self, name: str, timeout: int = 10) -> AbstractContextManager:
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
        # Modern (non-deprecated) collection creation logic:
        # 1. Prefer collection_exists + create_collection
        # 2. Fallback to get_collection (older clients) to detect presence
        # 3. Do NOT blindly drop existing collection to preserve data in real deployments
        # 4. If dimension mismatch occurs, we log (if logger available) and proceed – tests assume fresh start
        try:
            exists = False
            try:
                # Newer qdrant-client
                if hasattr(self.client, "collection_exists"):
                    exists = bool(self.client.collection_exists(self.collection_name))  # type: ignore[arg-type]
                else:  # pragma: no cover - older client path
                    self.client.get_collection(collection_name=self.collection_name)
                    exists = True
            except Exception:
                exists = False

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                )
            else:
                # Optional: verify dimension; skip heavy reconciliation for now
                try:
                    info = self.client.get_collection(collection_name=self.collection_name)
                    current_dim = None
                    # Structure differs by client version; attempt best-effort extraction
                    if hasattr(info, "config") and hasattr(info.config, "params"):
                        try:
                            current_dim = info.config.params.size  # type: ignore[attr-defined]
                        except Exception:  # pragma: no cover - defensive
                            current_dim = None
                    if current_dim and current_dim != vector_dim:
                        # Best-effort remediation: create an alternate collection name with correct dim
                        # (Avoid destructive recreate). Downstream code always references self.collection_name,
                        # so we only adjust name if mismatch discovered.
                        alt_name = f"{self.collection_name}_dim{vector_dim}"
                        if not (
                            hasattr(self.client, "collection_exists")
                            and self.client.collection_exists(alt_name)
                        ):
                            self.client.create_collection(
                                collection_name=alt_name,
                                vectors_config=VectorParams(
                                    size=vector_dim, distance=Distance.COSINE
                                ),
                            )
                        self.collection_name = alt_name
                except Exception:
                    # Non-fatal; continue with existing collection
                    pass
        except Exception:
            # Final fallback: attempt deprecated recreate_collection for extremely old clients
            try:  # pragma: no cover - legacy path
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
                )
            except Exception:
                pass

    def upsert(self, points: list[dict[str, Any]]):
        point_structs = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points
        ]
        self.client.upsert(collection_name=self.collection_name, wait=True, points=point_structs)

    def search(self, vector: list[float], top_k: int) -> list[Any]:
        # Prefer modern query_points API; fallback to deprecated search for older clients
        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=vector,  # type: ignore[arg-type]
                    limit=top_k,
                    with_payload=True,
                )
                # Newer client returns a QueryResponse with .points; older may already be a list
                points = getattr(response, "points", response)
                return points
        except Exception:
            # If modern path fails unexpectedly, fall back below
            pass
        # Legacy path
        return self.client.search(
            collection_name=self.collection_name, query_vector=vector, limit=top_k
        )

    def delete(self, ids: list[str]):
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
                SQL(
                    "CREATE TABLE IF NOT EXISTS {} (key TEXT PRIMARY KEY, value JSONB NOT NULL);"
                ).format(Identifier(self._TABLE_NAME))
            )
        # Best-effort: enable pg_trgm and add helpful indexes for keyword search
        try:
            with self._conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                # Trigram index on text representation for fast ILIKE searches
                cur.execute(
                    SQL(
                        "CREATE INDEX IF NOT EXISTS idx_{}_val_trgm ON {} USING gin ((value::text) gin_trgm_ops);"
                    ).format(Identifier(self._TABLE_NAME), Identifier(self._TABLE_NAME))
                )
                # Memory type expression index for optional filtering
                cur.execute(
                    SQL(
                        "CREATE INDEX IF NOT EXISTS idx_{}_memtype ON {} ((value->>'memory_type'));"
                    ).format(Identifier(self._TABLE_NAME), Identifier(self._TABLE_NAME))
                )
                # Namespace prefix on key to shrink scan for LIKE 'namespace:%:data'
                cur.execute(
                    SQL(
                        "CREATE INDEX IF NOT EXISTS idx_{}_key_prefix ON {} (key text_pattern_ops);"
                    ).format(Identifier(self._TABLE_NAME), Identifier(self._TABLE_NAME))
                )
        except Exception:
            # Non-fatal if permissions are restricted
            pass

    def set(self, key: str, value: bytes):
        # value is expected to be JSON-encoded bytes
        try:
            json_obj = json.loads(value)
        except Exception:
            # Fallback: store as plain string
            json_obj = value.decode("utf-8", errors="ignore")
        with self._conn.cursor() as cur:
            cur.execute(
                SQL(
                    "INSERT INTO {} (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;"
                ).format(Identifier(self._TABLE_NAME)),
                (key, Json(json_obj)),
            )

    def get(self, key: str) -> bytes | None:
        with self._conn.cursor() as cur:
            cur.execute(
                SQL("SELECT value FROM {} WHERE key = %s;").format(Identifier(self._TABLE_NAME)),
                (key,),
            )
            row = cur.fetchone()
            if row:
                # row[0] is a Python dict (psycopg2 converts JSONB to dict)
                return json.dumps(row[0]).encode("utf-8")
            return None

    def delete(self, key: str):
        with self._conn.cursor() as cur:
            cur.execute(
                SQL("DELETE FROM {} WHERE key = %s;").format(Identifier(self._TABLE_NAME)), (key,)
            )

    def scan_iter(self, pattern: str) -> Iterator[str]:
        # Convert glob pattern * to SQL %
        sql_pattern = pattern.replace("*", "%")
        with self._conn.cursor() as cur:
            cur.execute(
                SQL("SELECT key FROM {} WHERE key LIKE %s;").format(Identifier(self._TABLE_NAME)),
                (sql_pattern,),
            )
            for (k,) in cur.fetchall():
                yield k

    def hgetall(self, key: str) -> dict[bytes, bytes]:
        # Not used in core for canonical store; return empty dict.
        return {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        # Store mapping as JSON under the key (overwrites existing value).
        try:
            json_obj = {k.decode(): json.loads(v) for k, v in mapping.items()}
        except Exception:
            json_obj = {k.decode(): v.decode() for k, v in mapping.items()}
        self.set(key, json.dumps(json_obj).encode("utf-8"))

    def lock(self, name: str, timeout: int = 10) -> AbstractContextManager:
        return self._lock

    def health_check(self) -> bool:
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return True
        except Exception:
            return False

    # ---- Optional optimized keyword search (used opportunistically by core) ----
    def search_text(
        self,
        namespace: str,
        term: str,
        *,
        case_sensitive: bool = False,
        limit: int = 100,
        memory_type: str | None = None,
    ) -> list[dict]:
        pattern = f"{namespace}:%:data"
        like_op = "LIKE" if case_sensitive else "ILIKE"
        term_pattern = f"%{term}%"
        params: list[Any] = [pattern, term_pattern]
        where = ["key LIKE %s", f"value::text {like_op} %s"]
        if memory_type:
            where.append("(value->>'memory_type') = %s")
            params.append(memory_type)
        sql = f"SELECT value FROM {self._TABLE_NAME} WHERE " + " AND ".join(where) + " LIMIT %s;"
        params.append(limit)
        out: list[dict] = []
        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                for (val,) in cur.fetchall():
                    # val is dict from psycopg2 jsonb
                    if isinstance(val, dict):
                        out.append(val)
        except Exception:
            # Fallback silence – caller will use in-memory scan
            return []
        return out
