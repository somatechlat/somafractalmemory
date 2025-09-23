import logging
import os
from typing import Dict

import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

# Connection parameters – read from env or use defaults matching docker-compose.dev.yml
_DB_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://soma:soma@localhost:5432/soma",
)

# Lazy singleton connection
_conn = None


def _get_connection():
    global _conn
    if _conn is None:
        _conn = psycopg2.connect(_DB_URL)
        _conn.autocommit = True
        _ensure_table()
    return _conn


def _ensure_table():
    """Create the memory_events table if it does not exist."""
    with _conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_events (
                id UUID PRIMARY KEY,
                event_id UUID NOT NULL,
                namespace TEXT NOT NULL,
                type TEXT NOT NULL,
                timestamp DOUBLE PRECISION NOT NULL,
                payload JSONB NOT NULL
            );
            """
        )


def process_message(record: Dict) -> bool:
    """Upsert a memory event into Postgres.

    The function validates required fields, then performs an ``INSERT ... ON CONFLICT``
    upsert using the ``id`` column as the primary key. ``payload`` is stored as
    JSONB via ``psycopg2.extras.Json`` for proper typing.
    """
    required = ("event_id", "id", "namespace", "type", "timestamp", "payload")
    if not all(k in record for k in required):
        logger.warning("Record missing required fields: %s", record)
        return False

    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_events (id, event_id, namespace, type, timestamp, payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    event_id = EXCLUDED.event_id,
                    namespace = EXCLUDED.namespace,
                    type = EXCLUDED.type,
                    timestamp = EXCLUDED.timestamp,
                    payload = EXCLUDED.payload;
                """,
                (
                    record["id"],
                    record["event_id"],
                    record["namespace"],
                    record["type"],
                    float(record["timestamp"]),
                    Json(record["payload"]),
                ),
            )
        logger.info("Upserted event %s into Postgres", record["event_id"])
        return True
    except Exception as exc:  # pragma: no cover – runtime error handling
        logger.exception("Failed to upsert record into Postgres: %s", exc)
        return False
