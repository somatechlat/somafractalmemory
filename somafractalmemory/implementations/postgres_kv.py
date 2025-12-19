"""
PostgreSQL Key-Value Store implementation for SomaFractalMemory.

This module provides a PostgreSQL-backed implementation of the IKeyValueStore
interface, storing arbitrary keys with JSONB values.

Connection Pool Configuration:
- pool_size=10: Base number of connections to maintain
- max_overflow=20: Additional connections allowed under load
- pool_pre_ping=True: Verify connections before use
- pool_recycle=3600: Recycle connections after 1 hour
"""

import json
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager
from typing import Any

import psycopg2
from psycopg2 import OperationalError
from psycopg2 import errors as psycopg_errors
from psycopg2.extras import Json
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.sql import SQL, Identifier

from somafractalmemory.interfaces.storage import IKeyValueStore

# Module-level connection pool for sharing across instances
_connection_pools: dict[str, ThreadedConnectionPool] = {}
_pool_lock = threading.Lock()


def _get_connection_pool(url: str, **kwargs) -> ThreadedConnectionPool:
    """Get or create a shared connection pool for the given URL.

    This ensures multiple PostgresKeyValueStore instances share the same
    pool, preventing connection exhaustion during concurrent tenant operations.
    """
    with _pool_lock:
        if url not in _connection_pools:
            # Create pool with generous limits for concurrent tenant tests
            # minconn=2: Keep at least 2 connections ready
            # maxconn=30: Allow up to 30 concurrent connections
            _connection_pools[url] = ThreadedConnectionPool(
                minconn=2,
                maxconn=30,
                dsn=url,
                **kwargs,
            )
        return _connection_pools[url]


class PostgresKeyValueStore(IKeyValueStore):
    """Simple Postgres implementation of IKeyValueStore.

    Stores arbitrary keys with JSONB values in a table ``kv_store``.
    The table is created on first use if it does not exist.

    Uses a shared ThreadedConnectionPool to prevent connection exhaustion
    during concurrent tenant operations.
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
        self._pool: ThreadedConnectionPool | None = None
        self._conn = None
        self._lock = threading.RLock()
        self._ensure_connection()
        self._ensure_table()

    def _ensure_connection(self):
        """Get a connection from the pool or establish a new one."""
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

            # Try to use shared connection pool first
            try:
                self._pool = _get_connection_pool(self._url, **conn_kwargs)
                self._conn = self._pool.getconn()
                self._conn.autocommit = True
            except Exception:
                # Fallback to direct connection if pool fails
                self._pool = None
                self._conn = psycopg2.connect(self._url, **conn_kwargs)
                self._conn.autocommit = True

    def _reset_connection(self):
        """Return connection to pool or close it."""
        if self._conn is not None:
            try:
                if self._pool is not None:
                    # Return to pool instead of closing
                    self._pool.putconn(self._conn)
                else:
                    self._conn.close()
            except Exception:
                pass
        self._conn = None

    def _execute(self, fn: Callable[[Any], Any]) -> Any:
        """Execute a function with automatic connection recovery."""
        recoverable_errors: tuple[type[Exception], ...] = (
            psycopg2.InterfaceError,
            OperationalError,
            psycopg_errors.InFailedSqlTransaction,
        )

        def _run() -> Any:
            self._ensure_connection()
            # type: ignore[union-attr] - _conn is guaranteed non-None after _ensure_connection()
            with self._conn.cursor() as cur:  # type: ignore[union-attr]
                return fn(cur)

        try:
            return _run()
        except recoverable_errors:
            self._reset_connection()
            return _run()

    def _ensure_table(self):
        """Create the KV table and indexes if they don't exist."""

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
        """Store a key-value pair."""
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
        """Retrieve a value by key."""

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
        """Delete a key-value pair."""

        def _delete(cur):
            cur.execute(
                SQL("DELETE FROM {} WHERE key = %s;").format(Identifier(self._TABLE_NAME)),
                (key,),
            )

        self._execute(_delete)

    def scan_iter(self, pattern: str) -> Iterator[str]:
        """Iterate over keys matching a pattern."""
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
        """Not used in core for canonical store; return empty dict."""
        return {}

    def hset(self, key: str, mapping: Mapping[bytes, bytes]):
        """Store mapping as JSON under the key (overwrites existing value)."""
        try:
            json_obj = {k.decode(): json.loads(v) for k, v in mapping.items()}
        except Exception:
            json_obj = {k.decode(): v.decode() for k, v in mapping.items()}
        self.set(key, json.dumps(json_obj).encode("utf-8"))

    def lock(self, name: str, timeout: int = 10) -> AbstractContextManager:
        """Return an in-process lock (Postgres doesn't have distributed locks)."""
        return self._lock

    def health_check(self) -> bool:
        """Check if the database connection is healthy."""
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
        """Search for text within stored values."""
        import logging

        logger = logging.getLogger(__name__)

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
        except Exception as e:
            # Log the error; caller will use in-memory scan as fallback
            logger.debug("Postgres text search failed, caller will use in-memory scan: %s", e)
            return []
        return out
