"""PostgreSQL Key-Value Store implementation.

Provides key-value storage using psycopg3 (async-capable).
Used by SomaBrain for FNOM persistent storage.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PostgresKeyValueStore:
    """PostgreSQL-backed key-value store.

    Uses psycopg3 for async-capable database operations.
    """

    def __init__(
        self,
        dsn: str = "postgresql://soma:soma@localhost/somamemory",
        table_name: str = "kv_store",
    ):
        """Initialize PostgreSQL connection.

        Args:
            dsn: PostgreSQL connection string
            table_name: Name of the KV table
        """
        self.dsn = dsn
        self.table_name = table_name
        self._pool: Any | None = None

    def _get_connection(self):
        """Get a database connection."""
        import psycopg

        return psycopg.connect(self.dsn)

    def _ensure_table(self) -> None:
        """Ensure the KV table exists."""
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            key VARCHAR(512) PRIMARY KEY,
            value JSONB NOT NULL,
            namespace VARCHAR(255) DEFAULT 'default',
            tenant VARCHAR(255) DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_namespace
            ON {self.table_name}(namespace);
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_tenant
            ON {self.table_name}(tenant);
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_sql)
            conn.commit()

        logger.info(f"Ensured table {self.table_name} exists")

    def get(self, key: str, namespace: str = "default") -> dict[str, Any] | None:
        """Get a value by key.

        Args:
            key: The key to retrieve
            namespace: The namespace

        Returns:
            The value dict or None if not found
        """
        sql = f"""
        SELECT value FROM {self.table_name}
        WHERE key = %s AND namespace = %s
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (key, namespace))
                    row = cur.fetchone()
                    if row:
                        return row[0] if isinstance(row[0], dict) else json.loads(row[0])
                    return None
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: dict[str, Any],
        namespace: str = "default",
        tenant: str = "default",
    ) -> bool:
        """Set a key-value pair.

        Args:
            key: The key
            value: The value dict
            namespace: The namespace
            tenant: The tenant

        Returns:
            True if successful
        """
        sql = f"""
        INSERT INTO {self.table_name} (key, value, namespace, tenant, updated_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (key, json.dumps(value), namespace, tenant))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False

    def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete a key.

        Args:
            key: The key to delete
            namespace: The namespace

        Returns:
            True if deleted
        """
        sql = f"""
        DELETE FROM {self.table_name}
        WHERE key = %s AND namespace = %s
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (key, namespace))
                    deleted = cur.rowcount > 0
                conn.commit()
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    def list_keys(
        self,
        namespace: str = "default",
        prefix: str | None = None,
        limit: int = 100,
    ) -> list[str]:
        """List keys in a namespace.

        Args:
            namespace: The namespace
            prefix: Optional key prefix filter
            limit: Maximum keys to return

        Returns:
            List of keys
        """
        if prefix:
            sql = f"""
            SELECT key FROM {self.table_name}
            WHERE namespace = %s AND key LIKE %s
            ORDER BY key LIMIT %s
            """
            params = (namespace, f"{prefix}%", limit)
        else:
            sql = f"""
            SELECT key FROM {self.table_name}
            WHERE namespace = %s
            ORDER BY key LIMIT %s
            """
            params = (namespace, limit)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return []

    def count(self, namespace: str = "default") -> int:
        """Count keys in a namespace.

        Args:
            namespace: The namespace

        Returns:
            Number of keys
        """
        sql = f"""
        SELECT COUNT(*) FROM {self.table_name}
        WHERE namespace = %s
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (namespace,))
                    row = cur.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"Failed to count keys: {e}")
            return 0

    def health_check(self) -> bool:
        """Check if PostgreSQL is healthy."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False
