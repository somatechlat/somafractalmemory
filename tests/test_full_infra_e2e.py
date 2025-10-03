import json
import os
import socket
import time
import uuid

import pytest

# This test validates the full real infrastructure data path end-to-end:
# 1. Store memory via factory in EVENTED_ENTERPRISE mode
# 2. Assert Postgres canonical row exists
# 3. Assert Redis cache contains key (after retrieval)
# 4. Assert Qdrant vector point present (search hits marker)
# 5. Assert Kafka event published (memory.events topic)
# Skips gracefully if USE_REAL_INFRA!=1 or any backend unreachable.

REQUIRED_ENVS = [
    ("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5433/somamemory"),
    ("REDIS_HOST", "localhost"),
    ("REDIS_PORT", "6379"),
    ("QDRANT_HOST", "localhost"),
    ("QDRANT_PORT", "6333"),
    ("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"),  # compose outside broker mapping
]


def _tcp(host, port, timeout=1.0):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def _can_reach():
    for name, default in REQUIRED_ENVS:
        val = os.getenv(name, default)
        if name == "POSTGRES_URL":
            # parse host:port
            import re

            m = re.search(r"@([^:/]+):(\d+)", val)
            if m and not _tcp(m.group(1), int(m.group(2))):
                return False
        elif name == "KAFKA_BOOTSTRAP_SERVERS":
            host, port = val.split(",")[0].split(":")
            if not _tcp(host, int(port.split("/")[0])):
                return False
        elif name == "REDIS_HOST":
            if not _tcp(os.getenv("REDIS_HOST", default), int(os.getenv("REDIS_PORT", "6379"))):
                return False
        elif name == "QDRANT_HOST":
            if not _tcp(os.getenv("QDRANT_HOST", default), int(os.getenv("QDRANT_PORT", "6333"))):
                return False
    return True


@pytest.mark.integration
@pytest.mark.timeout(60)
def test_full_infra_e2e():
    if os.getenv("USE_REAL_INFRA") != "1":
        pytest.skip("Requires USE_REAL_INFRA=1")
    if not _can_reach():
        pytest.skip("Required infra not reachable")

    from somafractalmemory.core import MemoryType
    from somafractalmemory.factory import MemoryMode, create_memory_system

    namespace = os.getenv("SOMA_MEMORY_NAMESPACE", "api_ns")

    pg_url = os.getenv("POSTGRES_URL")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    config = {
        "postgres": {"url": pg_url},
        "redis": {"host": redis_host, "port": redis_port},
        "qdrant": {"host": qdrant_host, "port": qdrant_port},
        "eventing": {"enabled": True},
    }

    memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)

    marker = f"e2e-{uuid.uuid4()}"
    coord = (42.0, 24.0, 7.0)
    payload = {"task": marker, "importance": 3}
    memory.store_memory(coord, payload, memory_type=MemoryType.EPISODIC)

    # 1. Postgres canonical row
    import psycopg2

    conn = psycopg2.connect(pg_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT value FROM kv_store WHERE key LIKE %s",
            (f"{namespace}:%(42.0, 24.0, 7.0)%:data",),
        )
        # Fallback broader scan if direct key name quoting mismatch
        if cur.rowcount == 0:
            cur.execute(
                "SELECT value FROM kv_store WHERE key LIKE %s",
                (f"{namespace}:%(42.0, 24.0, 7.0)%",),
            )
        rows = cur.fetchall()
    assert rows, "Memory row not persisted in Postgres"
    # 2. Redis cache hit (after retrieval triggers caching)
    import redis as _redis

    r = _redis.Redis(host=redis_host, port=redis_port, db=0)
    # retrieval to push to cache
    _ = memory.retrieve(coord)
    # scan for namespace prefix
    has_key = any(
        k.decode() if isinstance(k, bytes) else str(k) for k in r.scan_iter(f"{namespace}:*")
    )
    assert has_key, "Redis does not show any namespace keys"

    # 3. Qdrant point presence (search by embedding of marker)
    from qdrant_client import QdrantClient

    qc = QdrantClient(host=qdrant_host, port=qdrant_port)
    # Basic attempt: similarity search using embed_text of marker payload
    emb = memory.embed_text(json.dumps(payload)).flatten().tolist()
    try:
        res = qc.query_points(collection_name=namespace, query=emb, limit=5, with_payload=True)
        points = getattr(res, "points", res)
    except Exception:
        points = qc.search(collection_name=namespace, query_vector=emb, limit=5)
    found_marker = any(
        marker == getattr(p, "payload", {}).get("task")  # modern QueryResponse point
        for p in points
        if getattr(p, "payload", None)
    )
    if not found_marker:
        # Hash‑based fallback: if similarity missed due to random hash embedding dispersion, perform a scroll
        try:
            scroll, _next = qc.scroll(collection_name=namespace, limit=200, with_payload=True)
            found_marker = any(
                getattr(p, "payload", {}).get("task") == marker
                for p in scroll
                if getattr(p, "payload", None)
            )
        except Exception:
            pass
    assert found_marker, "Qdrant search/scroll did not locate the stored payload"

    # 4. Kafka event (memory.events)
    try:
        from confluent_kafka import Consumer  # type: ignore
    except Exception as exc:
        pytest.skip(f"Kafka client missing: {exc}")
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    group_id = f"e2e-consumer-{int(time.time())}"
    consumer_conf = {
        "bootstrap.servers": bootstrap,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }
    consumer = Consumer(consumer_conf)
    topic = "memory.events"
    consumer.subscribe([topic])

    # Poll up to 20s for the marker payload
    deadline = time.time() + 20
    found = False
    while time.time() < deadline and not found:
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            continue
        try:
            evt = json.loads(msg.value())
            if evt.get("payload", {}).get("task") == marker:
                found = True
                break
        except Exception:
            continue
    consumer.close()
    assert found, "Kafka did not yield event with marker payload"

    # 5. Recreate memory system to ensure retrieval works (basic durability UI)
    memory2 = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)
    assert memory2.retrieve(coord), "Re-instantiated memory system failed to retrieve stored memory"
