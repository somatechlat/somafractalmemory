#!/usr/bin/env python
"""Manual full stack verification script.

Runs an end-to-end check against the currently configured real infrastructure.
Outputs a JSON summary of PASS/FAIL for each subsystem.

Usage:
  USE_REAL_INFRA=1 python scripts/verify_full_stack.py

Environment (defaults chosen for docker-compose):
  POSTGRES_URL=postgresql://postgres:postgres@localhost:5433/somamemory
  REDIS_HOST=localhost REDIS_PORT=6379
  QDRANT_HOST=localhost QDRANT_PORT=6333
  KAFKA_BOOTSTRAP_SERVERS=localhost:19092

Exit code 0 on full success, 1 if any component fails.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import uuid

SUMMARY = {
    "postgres": "SKIP",
    "redis": "SKIP",
    "qdrant": "SKIP",
    "kafka": "SKIP",
    "durability": "SKIP",
    "errors": [],
}


def _tcp(host: str, port: int, timeout: float = 1.0) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def main():
    if os.getenv("USE_REAL_INFRA") != "1":
        print(json.dumps({"error": "USE_REAL_INFRA not set"}, indent=2))
        return 1

    pg_url = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5433/somamemory")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
    namespace = os.getenv("SOMA_MEMORY_NAMESPACE", "api_ns")

    # Basic reachability
    # Postgres parse
    import re

    m = re.search(r"@([^:/]+):(\d+)", pg_url)
    if m and not _tcp(m.group(1), int(m.group(2))):
        SUMMARY["errors"].append("postgres unreachable")
    if not _tcp(redis_host, redis_port):
        SUMMARY["errors"].append("redis unreachable")
    if not _tcp(qdrant_host, qdrant_port):
        SUMMARY["errors"].append("qdrant unreachable")
    b_host, b_port = kafka_bootstrap.split(",")[0].split(":")
    if not _tcp(b_host, int(b_port.split("/")[0])):
        SUMMARY["errors"].append("kafka unreachable")

    from somafractalmemory.core import MemoryType
    from somafractalmemory.factory import MemoryMode, create_memory_system

    config = {
        "postgres": {"url": pg_url},
        "redis": {"host": redis_host, "port": redis_port},
        "qdrant": {"host": qdrant_host, "port": qdrant_port},
        "eventing": {"enabled": True},
    }

    memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)
    marker = f"verify-{uuid.uuid4()}"
    coord = (9.0, 9.0, 9.0)
    payload = {"task": marker, "importance": 2}
    memory.store_memory(coord, payload, memory_type=MemoryType.EPISODIC)

    # Postgres check
    try:
        import psycopg2

        conn = psycopg2.connect(pg_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM kv_store WHERE key LIKE %s", (f"{namespace}:%(9.0, 9.0, 9.0)%:data",)
            )
            if cur.rowcount == 0:
                cur.execute(
                    "SELECT 1 FROM kv_store WHERE key LIKE %s", (f"{namespace}:%(9.0, 9.0, 9.0)%",)
                )
            SUMMARY["postgres"] = "PASS" if cur.rowcount > 0 else "FAIL"
            if cur.rowcount == 0:
                SUMMARY["errors"].append("postgres row missing")
    except Exception as e:
        SUMMARY["postgres"] = "FAIL"
        SUMMARY["errors"].append(f"postgres error: {e}")

    # Redis check
    try:
        import redis as _redis

        r = _redis.Redis(host=redis_host, port=redis_port, db=0)
        memory.retrieve(coord)  # warm cache
        has_key = any(True for _ in r.scan_iter(f"{namespace}:*"))
        SUMMARY["redis"] = "PASS" if has_key else "FAIL"
        if not has_key:
            SUMMARY["errors"].append("redis key missing")
    except Exception as e:
        SUMMARY["redis"] = "FAIL"
        SUMMARY["errors"].append(f"redis error: {e}")

    # Qdrant check
    try:
        from qdrant_client import QdrantClient

        emb = memory.embed_text(json.dumps(payload)).flatten().tolist()
        qc = QdrantClient(host=qdrant_host, port=qdrant_port)
        try:
            res = qc.query_points(collection_name=namespace, query=emb, limit=3, with_payload=True)
            points = getattr(res, "points", res)
        except Exception:
            points = qc.search(collection_name=namespace, query_vector=emb, limit=3)
        ok = any(getattr(p, "payload", {}).get("task") == marker for p in points)
        SUMMARY["qdrant"] = "PASS" if ok else "FAIL"
        if not ok:
            SUMMARY["errors"].append("qdrant missing marker payload")
    except Exception as e:
        SUMMARY["qdrant"] = "FAIL"
        SUMMARY["errors"].append(f"qdrant error: {e}")

    # Kafka check
    try:
        from confluent_kafka import Consumer  # type: ignore

        group_id = f"verify-consumer-{int(time.time())}"
        consumer_conf = {
            "bootstrap.servers": kafka_bootstrap,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
        consumer = Consumer(consumer_conf)
        topic = "memory.events"
        consumer.subscribe([topic])
        deadline = time.time() + 15
        found = False
        while time.time() < deadline and not found:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            try:
                evt = json.loads(msg.value())
                if evt.get("payload", {}).get("task") == marker:
                    found = True
            except Exception:
                continue
        consumer.close()
        SUMMARY["kafka"] = "PASS" if found else "FAIL"
        if not found:
            SUMMARY["errors"].append("kafka event not observed")
    except Exception as e:
        SUMMARY["kafka"] = "FAIL"
        SUMMARY["errors"].append(f"kafka error: {e}")

    # Durability basic: new memory system retrieve
    try:
        from somafractalmemory.factory import MemoryMode, create_memory_system

        memory2 = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)
        SUMMARY["durability"] = "PASS" if memory2.retrieve(coord) else "FAIL"
        if SUMMARY["durability"] == "FAIL":
            SUMMARY["errors"].append("durability retrieval failed")
    except Exception as e:
        SUMMARY["durability"] = "FAIL"
        SUMMARY["errors"].append(f"durability error: {e}")

    ok = all(v == "PASS" for k, v in SUMMARY.items() if k not in {"errors"})
    print(json.dumps(SUMMARY, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
