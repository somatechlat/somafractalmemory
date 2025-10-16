import os
import time

import pytest

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.mark.integration
def test_full_stack_round_trip_real_infra():
    """End‑to‑end assertion that a SMALL batch of memories flows through the entire
    enterprise stack (Postgres + Redis + Qdrant + Kafka event emit) when
    USE_REAL_INFRA=1 is set and real services are running via docker-compose.

    This test intentionally:
    - Uses EVENTED_ENTERPRISE mode to force Qdrant remote usage (host/port) and eventing.
    - Writes N memories (episodic) with distinct coordinates.
    - Polls recall() to ensure the vector layer indexed them (Qdrant).
    - Directly inspects kv_store scan_iter to ensure Postgres/Redis persistence for keys.
    - Verifies health_check() for all backends.
    - (Indirect Kafka check) Ensures no exception was raised publishing events; if Kafka is
      down the producer would have thrown and store_memory would log warnings. We assert
      absence of WAL entries indicating vector insertion failures.
    """

    if os.getenv("USE_REAL_INFRA") != "1":  # Safety guard
        pytest.skip("Requires USE_REAL_INFRA=1 and running docker-compose stack")

    # Assemble real infra config from environment (docker-compose assigns ports)
    pg_url = os.getenv("POSTGRES_URL", "postgresql://soma:soma@postgres:40001/soma")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "40002"))
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "40003"))

    config = {
        "postgres": {"url": pg_url},
        "redis": {"host": redis_host, "port": redis_port},
        "qdrant": {"host": qdrant_host, "port": qdrant_port},
        "eventing": {"enabled": True},
    }

    namespace = "full_stack_it"
    mem = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)
    mem._reconcile_once()  # Clear stale WAL entries from previous runs

    N = 5
    coords: list[tuple[float, float, float]] = []
    for i in range(N):
        coord = (float(i), float(i + 1), float(i + 2))
        payload = {
            "task": f"integration-store-{i}",
            "importance": i + 1,
            "meta": {"iteration": i},
        }
        mem.store_memory(coord, payload, memory_type=MemoryType.EPISODIC)
        coords.append(coord)

    # Postgres/Redis keys check: ensure data key exists for each coordinate
    missing = []
    for c in coords:
        data_key = f"{namespace}:{repr(c)}:data"
        if mem.kv_store.get(data_key) is None:
            missing.append(data_key)
    assert not missing, f"Missing KV entries for: {missing}"

    # Qdrant vector index recall: poll until at least N memories retrievable via hybrid recall
    # (The embedding is hash-based or model-based; we just ensure some results appear.)
    deadline = time.time() + 10
    retrieved_payloads = []
    while time.time() < deadline:
        results = mem.recall("integration-store", top_k=N)
        retrieved_payloads = [
            r for r in results if r.get("task", "").startswith("integration-store-")
        ]
        if len(retrieved_payloads) >= N:
            break
        time.sleep(0.5)
    assert len(retrieved_payloads) >= N, "Vector recall did not surface all stored memories in time"

    # Health check of all three primary backends
    health = mem.health_check()
    assert health.get("kv_store") is True
    assert health.get("vector_store") is True
    assert health.get("graph_store") is True

    # WAL absence: ensure no uncommitted WAL entries indicating vector failures
    wal_prefix = f"{namespace}:wal:"
    wal_leaks = [k for k in mem.kv_store.scan_iter(f"{wal_prefix}*")]
    assert not wal_leaks, f"Unexpected WAL entries present: {wal_leaks}"

    # Spot check access_count increment path by retrieving one memory explicitly
    one = coords[0]
    m1 = mem.retrieve(one)
    assert m1 is not None and m1.get("access_count", 0) >= 1

    # Lock + set_importance round-trip on a coordinate to exercise Redis lock path
    mem.set_importance(one, importance=42)
    updated = mem.retrieve(one)
    assert updated and updated.get("importance") == 42

    # Namespace isolation: ensure keys are all namespaced correctly
    stray = [
        k for k in mem.kv_store.scan_iter(f"*{repr(coords[0])}:data") if not k.startswith(namespace)
    ]
    assert not stray, f"Found stray keys outside namespace: {stray}"

    # If we got here all subsystems cooperated.
