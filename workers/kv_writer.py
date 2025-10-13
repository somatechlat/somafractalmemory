import os
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import Json

from common.utils.logger import get_logger

logger = get_logger("somafractalmemory").bind(component="kv_writer")


# Connection parameters – prefer explicit env; otherwise fall back to centralized settings DNS.
def _resolve_db_url() -> str:
    env_url = os.getenv("POSTGRES_URL")
    if env_url:
        return env_url
    # Optional centralized settings (if available); do not hard‑fail if missing
    try:
        from common.config.settings import load_settings  # type: ignore

        _s = load_settings()
        host = getattr(getattr(_s, "infra", None), "postgres", None)
        if host:
            # Defaults align with Helm values and compose: postgres/postgres@<host>:5432/somamemory
            return f"postgresql://postgres:postgres@{host}:5432/somamemory"
    except Exception:
        pass
    # Final fallback: local developer default
    return "postgresql://postgres:postgres@localhost:5433/somamemory"


_DB_URL = _resolve_db_url()

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


def process_message(record: dict) -> bool:
    """Upsert a memory event into Postgres.

    The function validates required fields, then performs an ``INSERT ... ON CONFLICT``
    upsert using the ``id`` column as the primary key. ``payload`` is stored as
    JSONB via ``psycopg2.extras.Json`` for proper typing.
    """
    required = ("event_id", "id", "namespace", "type", "timestamp", "payload")
    if not all(k in record for k in required):
        logger.warning("Record missing required fields", record=record)
        return False

    conn = _get_connection()
    try:
        # Normalize timestamp: accept numeric epoch or ISO8601 string
        ts_val = record["timestamp"]
        try:
            ts_float = float(ts_val)
        except Exception:
            # Attempt to parse ISO8601 (handle 'Z' suffix)
            if isinstance(ts_val, str):
                try:
                    if ts_val.endswith("Z"):
                        ts_val = ts_val[:-1] + "+00:00"
                    dt = datetime.fromisoformat(ts_val)
                    ts_float = dt.replace(tzinfo=dt.tzinfo or timezone.utc).timestamp()
                except Exception:
                    # Last resort: use current time
                    ts_float = datetime.now(timezone.utc).timestamp()
            else:
                ts_float = datetime.now(timezone.utc).timestamp()

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
                    ts_float,
                    Json(record["payload"]),
                ),
            )
        logger.info("Upserted event into Postgres", event_id=record["event_id"])
        return True
    except Exception as exc:  # pragma: no cover – runtime error handling
        logger.exception("Failed to upsert record into Postgres", error=str(exc))
        return False
