"""
Storage implementations for SomaFractalMemory.
"""

# Standard library imports
import inspect
import json
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager
from typing import Any, Optional

# Third‑party imports (alphabetical)
import psycopg2
import redis
from psycopg2 import OperationalError
from psycopg2 import errors as psycopg_errors

try:
    # Optional OpenTelemetry instrumentation; safe no-op when package missing
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor  # type: ignore
except Exception:  # pragma: no cover - optional dependency path
    Psycopg2Instrumentor = None  # type: ignore

# Specific third‑party imports
# Qdrant client imports - required for QdrantVectorStore (used in local testing)
try:
    import qdrant_client
    from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False
    qdrant_client = None  # type: ignore

from psycopg2.extras import Json
from psycopg2.sql import SQL, Identifier
from redis.exceptions import ConnectionError

# Local application imports
from somafractalmemory.core import VectorStoreError
from somafractalmemory.interfaces.storage import IKeyValueStore, IVectorStore

# Module-level caches for shared connection objects to enable connection
# pooling and client reuse across multiple store instances. This reduces
# connection churn under high QPS and avoids creating many short-lived
# connections when multiple Memory instances are constructed.
_redis_connection_pools: dict[tuple[str, int, int], redis.ConnectionPool] = {}
_qdrant_clients: dict[tuple, Any] = {}  # Cache for Qdrant clients

# Initialise instrumentation (executed at import time) if available
if Psycopg2Instrumentor is not None:  # pragma: no cover - optional dependency path
    try:
        Psycopg2Instrumentor().instrument()
    except Exception:
        # Never let instrumentation failures break core functionality
        pass


# NOTE: In‑memory KV and Vector stores have been **removed** to enforce the
# “real‑infrastructure‑only” policy. The production code now relies exclusively
# on `RedisKeyValueStore`, `PostgresRedisHybridStore`, and `MilvusVectorStore`.


class RedisKeyValueStore(IKeyValueStore):
    """Redis implementation of the key‑value store interface.

    All testing‑related branches and in‑process fallbacks have been removed per
    the Vibe Coding Rules. The store now always operates against a real Redis
    instance created via a shared connection pool.
    """

    def lock(self, name: str, timeout: int = 10) -> AbstractContextManager:
        # Directly delegate to the Redis client lock implementation.
        return self.client.lock(name, timeout=timeout)

    def health_check(self) -> bool:
        try:
            return bool(self.client.ping())
        except ConnectionError:
            return False

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        # Create (or reuse) a connection pool for the given host/port/db.
        pool_key = (str(host), int(port), int(db))
        pool = _redis_connection_pools.get(pool_key)
        if pool is None:
            pool = redis.ConnectionPool(host=host, port=port, db=db)
            _redis_connection_pools[pool_key] = pool
        self.client = redis.Redis(connection_pool=pool)

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


# ---------------------------------------------------------------------
# Qdrant implementation (for local testing with on-disk storage)
# ---------------------------------------------------------------------
# NOTE: QdrantVectorStore is kept for local testing scenarios where an
# on-disk vector store is needed without running a full Milvus cluster.
# Production deployments use MilvusVectorStore exclusively.


class QdrantVectorStore(IVectorStore):
    """Qdrant implementation of the vector store interface.

    Used primarily for local testing with on-disk storage. Production
    deployments should use MilvusVectorStore.
    """

    def __init__(self, collection_name: str, **kwargs):
        if not _QDRANT_AVAILABLE:
            raise VectorStoreError(
                "qdrant-client is required for QdrantVectorStore. "
                "Install with: pip install qdrant-client"
            )
        self._init_kwargs = kwargs
        # Attempt to reuse a shared Qdrant client when the same connection
        # parameters are used multiple times.
        try:
            key = tuple(sorted((k, str(v)) for k, v in self._init_kwargs.items()))
        except Exception:
            key = tuple(sorted(list(self._init_kwargs.items())))
        cached = _qdrant_clients.get(key)
        if cached is not None:
            self.client = cached
        else:
            client = qdrant_client.QdrantClient(**self._init_kwargs)
            _qdrant_clients[key] = client
            self.client = client
        self.collection_name = collection_name

    @property
    def is_on_disk(self) -> bool:
        """Checks if the Qdrant client is using on-disk storage."""
        if "url" in self._init_kwargs or "host" in self._init_kwargs:
            return False
        path = self._init_kwargs.get("path")
        location = self._init_kwargs.get("location")
        return path is not None and path != ":memory:" and location != ":memory:"

    def setup(self, vector_dim: int, namespace: str):
        self.collection_name = namespace
        try:
            exists = False
            if hasattr(self.client, "collection_exists"):
                exists = bool(self.client.collection_exists(self.collection_name))
            else:
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
            pass

    def upsert(self, points: list[dict[str, Any]]):
        point_structs = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points
        ]
        self.client.upsert(collection_name=self.collection_name, wait=True, points=point_structs)

    def search(self, vector: list[float], top_k: int) -> list[Any]:
        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    limit=top_k,
                    with_payload=True,
                )
                points = getattr(response, "points", response)
                return points
        except Exception:
            pass
        return self.client.search(
            collection_name=self.collection_name, query_vector=vector, limit=top_k
        )

    def delete(self, ids: list[str]):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=[i for i in ids if i]),
            wait=True,
        )

    def scroll(self) -> Iterator[Any]:
        _lim = 100
        records, next_page_offset = self.client.scroll(
            collection_name=self.collection_name,
            limit=_lim,
            with_payload=True,
            with_vectors=True,
        )
        while records:
            yield from records
            if next_page_offset is None:
                break
            records, next_page_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=_lim,
                with_payload=True,
                offset=next_page_offset,
            )

    def health_check(self) -> bool:
        try:
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------
# Milvus implementation (production vector backend)
# ---------------------------------------------------------------------
# NOTE: Milvus is the production vector backend. MilvusVectorStore is used
# by the factory for all production deployments.
# Uses the official `pymilvus` client. All network‑related errors are wrapped
# in `VectorStoreError` to keep error handling consistent across backends.


class MilvusVectorStore(IVectorStore):
    """Milvus implementation of the vector‑store interface.

    The constructor expects a collection name and connection kwargs. The
    `setup` method creates the collection with the required schema if it does
    not already exist.
    """

    def __init__(self, collection_name: str, **kwargs):
        # Import pymilvus - required for Milvus (exclusive vector backend)
        try:
            from pymilvus import Collection, connections, utility
        except ImportError as exc:
            raise VectorStoreError("pymilvus is required for Milvus backend") from exc

        self.collection_name = collection_name
        self._init_kwargs = kwargs
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 19530)
        # Establish a default connection (named "default").
        connections.connect(alias="default", host=host, port=port)
        self._connections = connections
        self._Collection = Collection
        self._utility = utility

    # -----------------------------------------------------------------
    def setup(self, vector_dim: int, namespace: str):
        # Use namespace as collection name if not already set.
        self.collection_name = namespace
        # Check if collection exists; create if missing.
        if not self._utility.has_collection(self.collection_name):
            from pymilvus import CollectionSchema, DataType, FieldSchema

            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=255),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
                FieldSchema(name="payload", dtype=DataType.JSON),
            ]
            schema = CollectionSchema(fields, description="SomaFractalMemory vectors")
            self._Collection(name=self.collection_name, schema=schema)
        else:
            # Verify dimension matches expected size.
            coll = self._Collection(self.collection_name)
            vec_field = next(f for f in coll.schema.fields if f.name == "embedding")
            if vec_field.params.get("dim") != vector_dim:
                raise VectorStoreError(
                    f"Milvus collection dimension {vec_field.params.get('dim')} does not match required {vector_dim}"
                )

    # -----------------------------------------------------------------
    def upsert(self, points: list[dict[str, Any]]):
        ids = [p["id"] for p in points]
        vectors = [p["vector"] for p in points]
        payloads = [p["payload"] for p in points]
        coll = self._Collection(self.collection_name)
        try:
            coll.insert([ids, vectors, payloads])
        except Exception as exc:
            raise VectorStoreError("Milvus upsert failed") from exc

    # -----------------------------------------------------------------
    def search(self, vector: list[float], top_k: int) -> list[Any]:
        from pymilvus import SearchParam

        coll = self._Collection(self.collection_name)
        try:
            results = coll.search(
                data=[vector],
                anns_field="embedding",
                param=SearchParam(metric_type="IP", params={"nprobe": 10}),
                limit=top_k,
                expr=None,
                output_fields=["payload"],
            )
            # `results` is a list of lists; flatten.
            return [hit for sublist in results for hit in sublist]
        except Exception as exc:
            raise VectorStoreError("Milvus search failed") from exc

    # -----------------------------------------------------------------
    def delete(self, ids: list[str]):
        """Delete vectors by their primary IDs.

        Modern Milvus SDK versions provide ``delete(ids=...)``. For backward
        compatibility we fall back to the expression‑based syntax if the newer
        signature is unavailable.
        """
        if not ids:
            return
        coll = self._Collection(self.collection_name)
        try:
            # Prefer the native ``ids`` argument supported by modern Milvus SDKs.
            coll.delete(ids=ids)  # type: ignore[arg-type]
        except Exception:
            # Fallback to expression syntax for legacy clients.
            try:
                ids_quoted = ",".join([f'"{i}"' for i in ids])
                expr = f"id in [{ids_quoted}]"
                coll.delete(expr=expr)
            except Exception as exc:
                raise VectorStoreError("Milvus delete failed") from exc

    # -----------------------------------------------------------------
    def scroll(self) -> Iterator[Any]:
        # Milvus does not provide a native scroll; emulate with offset pagination.
        coll = self._Collection(self.collection_name)
        batch = 1000
        offset = 0
        while True:
            records = coll.query(
                expr="", output_fields=["id", "embedding", "payload"], limit=batch, offset=offset
            )
            if not records:
                break
            yield from records
            offset += batch

    # -----------------------------------------------------------------
    def health_check(self) -> bool:
        try:
            return self._utility.has_collection(self.collection_name)
        except Exception:
            return False


class BatchedStore(IKeyValueStore, IVectorStore):
    """Wraps a KV store and a Vector store and batches writes in-process.

    This class is opt-in via configuration (env var). It collects KV `set`
    calls and vector `upsert` calls into an in-memory queue and flushes them
    periodically or when a configured batch size is reached. The flush runs
    on a daemon background thread so it doesn't block request processing.
    """

    def __init__(
        self,
        kv_store: IKeyValueStore,
        vector_store: IVectorStore,
        batch_size: int = 100,
        flush_interval_ms: int = 5,
    ):
        self._kv = kv_store
        self._vec = vector_store
        self._batch_size = int(batch_size)
        self._flush_interval = max(int(flush_interval_ms), 1) / 1000.0
        self._kv_queue: list[tuple[str, bytes]] = []
        self._vec_queue: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    # ----- IKeyValueStore methods (delegated where appropriate) -----
    def set(self, key: str, value: bytes):
        # Enqueue KV set for batch flush
        with self._lock:
            self._kv_queue.append((key, value))
            if len(self._kv_queue) + len(self._vec_queue) >= self._batch_size:
                # flush synchronously when threshold reached to avoid unbounded memory
                self._flush_locked()

    def get(self, key: str) -> bytes | None:
        # Reads must be strongly consistent; delegate directly to underlying store
        return self._kv.get(key)

    def delete(self, key_or_ids):
        """Delete either a KV key (str) or vector ids (list[str]).

        BatchedStore implements both IKeyValueStore and IVectorStore delete
        contracts. To avoid duplicate method names with incompatible
        signatures, provide a single dispatcher that accepts either a string
        key (delegated to the underlying KV store) or an iterable of ids
        (delegated to the underlying vector store).
        """
        # Vector delete path (list/tuple of ids)
        try:
            if isinstance(key_or_ids, list) or isinstance(key_or_ids, tuple):
                return self._vec.delete(key_or_ids)
        except Exception:
            # Fallthrough to KV path
            pass
        # KV delete path (single key)
        return self._kv.delete(key_or_ids)

    def scan_iter(self, pattern: str):
        return self._kv.scan_iter(pattern)

    def hgetall(self, key: str) -> dict[bytes, bytes]:
        return self._kv.hgetall(key)

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        return self._kv.hset(key, mapping)

    def lock(self, name: str, timeout: int = 10):
        return self._kv.lock(name, timeout)

    def health_check(self) -> bool:
        return self._kv.health_check() and self._vec.health_check()

    # ----- IVectorStore methods -----
    def setup(self, vector_dim: int, namespace: str):
        return self._vec.setup(vector_dim, namespace)

    def upsert(self, points: list[dict[str, Any]]):
        # Enqueue points for batch upsert
        with self._lock:
            self._vec_queue.extend(points)
            if len(self._kv_queue) + len(self._vec_queue) >= self._batch_size:
                self._flush_locked()

    def search(self, vector: list[float], top_k: int):
        return self._vec.search(vector, top_k)

    # (vector delete is handled by the unified `delete` dispatcher above)

    def scroll(self):
        return self._vec.scroll()

    # ----- Background worker & flush -----
    def _run(self):
        while not self._stop.is_set():
            try:
                with self._lock:
                    self._flush_locked()
            except Exception:
                # Avoid letting background thread crash silently
                pass
            self._stop.wait(self._flush_interval)

    def _flush_locked(self):
        # Caller must hold self._lock
        if not self._kv_queue and not self._vec_queue:
            return
        kv_items = self._kv_queue
        vec_items = self._vec_queue
        self._kv_queue = []
        self._vec_queue = []

        # Flush KV items
        try:
            # Best-effort: try to use pipeline if underlying Redis client exposes it
            if hasattr(self._kv, "client") and hasattr(self._kv.client, "pipeline"):
                pipe = self._kv.client.pipeline()
                for k, v in kv_items:
                    pipe.set(k, v)
                try:
                    pipe.execute()
                except Exception:
                    # Fallback to individual writes
                    for k, v in kv_items:
                        try:
                            self._kv.set(k, v)
                        except Exception:
                            pass
            else:
                for k, v in kv_items:
                    try:
                        self._kv.set(k, v)
                    except Exception:
                        pass
        except Exception:
            pass

        # Flush vector items
        try:
            if vec_items:
                try:
                    self._vec.upsert(vec_items)
                except Exception:
                    # If upsert fails, attempt individual upserts to avoid losing data
                    for p in vec_items:
                        try:
                            self._vec.upsert([p])
                        except Exception:
                            pass
        except Exception:
            pass

    def flush(self, timeout: float = 5.0):
        """Flush pending items synchronously (useful for tests)."""
        ev = threading.Event()
        with self._lock:
            self._flush_locked()
        ev.wait(0)

    def stop(self):
        self._stop.set()
        try:
            self._worker.join(timeout=1.0)
        except Exception:
            pass

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass


# Postgres-backed key-value store (canonical storage for EVENTED_ENTERPRISE)


class PostgresKeyValueStore(IKeyValueStore):
    """Simple Postgres implementation of IKeyValueStore.

    Stores arbitrary keys with JSONB values in a table ``kv_store``.
    The table is created on first use if it does not exist.
    """

    _TABLE_NAME = "kv_store"

    def __init__(self, url: str | None = None):
        # Centralised configuration for Postgres connection.
        from common.config.settings import load_settings

        _settings = load_settings()
        # Prefer explicit URL argument, then settings, then default fallback.
        raw_url = (
            url
            or getattr(_settings, "postgres_url", None)
            or "postgresql://soma:soma@localhost:5432/soma"
        )
        # Strip the ``+psycopg2`` dialect suffix if present.
        self._url = raw_url.replace("postgresql+psycopg2://", "postgresql://", 1)
        # TLS/SSL configuration – optional settings fields.
        self._sslmode = getattr(_settings, "postgres_ssl_mode", None)
        self._sslrootcert = getattr(_settings, "postgres_ssl_root_cert", None)
        self._sslcert = getattr(_settings, "postgres_ssl_cert", None)
        self._sslkey = getattr(_settings, "postgres_ssl_key", None)
        self._conn = None
        self._lock = threading.RLock()
        self._ensure_connection()
        self._ensure_table()

    def _ensure_connection(self):
        # Establish a new connection if none exists or if the previous
        # connection has been closed by the server (e.g., container restart).
        if self._conn is None or getattr(self._conn, "closed", 0) != 0:
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

    def _reset_connection(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None

    def _execute(self, fn: Callable[[Any], Any]) -> Any:
        recoverable_errors: tuple[type[Exception], ...] = (
            psycopg2.InterfaceError,
            OperationalError,
            psycopg_errors.InFailedSqlTransaction,
        )

        def _run() -> Any:
            self._ensure_connection()
            with self._conn.cursor() as cur:  # type: ignore[union-attr]
                return fn(cur)

        try:
            return _run()
        except recoverable_errors:
            self._reset_connection()
            return _run()

    def _ensure_table(self):
        def _create(cur):
            cur.execute(
                SQL(
                    "CREATE TABLE IF NOT EXISTS {} (key TEXT PRIMARY KEY, value JSONB NOT NULL);"
                ).format(Identifier(self._TABLE_NAME))
            )

        self._execute(_create)
        # Best-effort: enable pg_trgm and add helpful indexes for keyword search
        try:

            def _indexes(cur):
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                cur.execute(
                    SQL(
                        "CREATE INDEX IF NOT EXISTS idx_{}_val_trgm ON {} USING gin ((value::text) gin_trgm_ops);"
                    ).format(Identifier(self._TABLE_NAME), Identifier(self._TABLE_NAME))
                )
                cur.execute(
                    SQL(
                        "CREATE INDEX IF NOT EXISTS idx_{}_memtype ON {} ((value->>'memory_type'));"
                    ).format(Identifier(self._TABLE_NAME), Identifier(self._TABLE_NAME))
                )
                cur.execute(
                    SQL(
                        "CREATE INDEX IF NOT EXISTS idx_{}_key_prefix ON {} (key text_pattern_ops);"
                    ).format(Identifier(self._TABLE_NAME), Identifier(self._TABLE_NAME))
                )

            self._execute(_indexes)
        except Exception:
            # Non-fatal if permissions are restricted
            pass

    def set(self, key: str, value: bytes):
        # value is expected to be JSON-encoded bytes
        self._ensure_connection()
        try:
            json_obj = json.loads(value)
        except Exception:
            # Fallback: store as plain string
            json_obj = value.decode("utf-8", errors="ignore")
        payload = Json(json_obj)

        def _write(cur):
            cur.execute(
                SQL(
                    "INSERT INTO {} (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;"
                ).format(Identifier(self._TABLE_NAME)),
                (key, payload),
            )

        self._execute(_write)

    def get(self, key: str) -> bytes | None:
        def _read(cur):
            cur.execute(
                SQL("SELECT value FROM {} WHERE key = %s;").format(Identifier(self._TABLE_NAME)),
                (key,),
            )
            return cur.fetchone()

        row = self._execute(_read)
        if row:
            # row[0] is a Python dict (psycopg2 converts JSONB to dict)
            return json.dumps(row[0]).encode("utf-8")
        return None

    def delete(self, key: str):
        def _delete(cur):
            cur.execute(
                SQL("DELETE FROM {} WHERE key = %s;").format(Identifier(self._TABLE_NAME)),
                (key,),
            )

        self._execute(_delete)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        # Convert glob pattern * to SQL %
        sql_pattern = pattern.replace("*", "%")

        def _scan(cur):
            cur.execute(
                SQL("SELECT key FROM {} WHERE key LIKE %s;").format(Identifier(self._TABLE_NAME)),
                (sql_pattern,),
            )
            return cur.fetchall()

        rows = self._execute(_scan)
        for (k,) in rows:
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
            self._execute(lambda cur: cur.execute("SELECT 1;"))
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
