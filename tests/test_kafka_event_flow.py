import os
import time
from collections import Counter

import pytest

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


@pytest.mark.integration
def test_kafka_event_flow_real_infra():
    """Validate that storing memories in EVENTED_ENTERPRISE mode produces Kafka events.

    Strategy:
    1. Require USE_REAL_INFRA=1 and confluent_kafka to be installed in the runtime.
    2. Create an EVENTED_ENTERPRISE memory system with eventing enabled, pointing at real services.
    3. Create a consumer subscribed to the 'memory.events' topic; poll current position (baseline).
    4. Store N episodic memories; each should publish one 'created' event.
    5. Poll the consumer until >= N new matching events are read (or timeout) and validate schema fields.
    """

    if os.getenv("USE_REAL_INFRA") != "1":
        pytest.skip("Requires USE_REAL_INFRA=1 and running docker-compose stack")

    try:
        from confluent_kafka import Consumer  # type: ignore
    except Exception as exc:
        pytest.skip(f"confluent_kafka not available in test environment: {exc}")

    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    detected_namespace_env = os.getenv("SOMA_NAMESPACE")
    group_id = f"test-consumer-{int(time.time())}"
    topic = "memory.events"

    consumer_conf = {
        "bootstrap.servers": bootstrap,
        "group.id": group_id,
        # Use earliest plus position seek to end after initial assignment to robustly
        # handle auto-create topic timing; we'll record current end offsets manually.
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "enable.partition.eof": True,
    }
    consumer = Consumer(consumer_conf)
    consumer.subscribe([topic])

    # Build enterprise memory system configuration
    pg_url = os.getenv("POSTGRES_URL", "postgresql://soma:soma@postgres:5432/soma")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    namespace = "kafka_it"
    config = {
        "postgres": {"url": pg_url},
        "redis": {"host": redis_host, "port": redis_port},
        "qdrant": {"host": qdrant_host, "port": qdrant_port},
        "eventing": {"enabled": True},
    }

    memory = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, namespace, config=config)
    effective_namespace = detected_namespace_env or namespace

    # Establish baseline (assignments + move to end BEFORE producing test events)
    start_deadline = time.time() + 10
    assignments = []
    while time.time() < start_deadline:
        m = consumer.poll(0.5)
        if m is None:
            pass
        elif m.error() and not str(m.error()).startswith("_STATE"):
            # Ignore benign internal state codes
            pass
        assignments = consumer.assignment()
        if assignments:
            # Move each assigned partition to its current high watermark (end)
            new_positions = []
            for tp in assignments:
                try:
                    low, high = consumer.get_watermark_offsets(tp)
                    tp.offset = high  # start from end for new messages only
                    new_positions.append(tp)
                except Exception:
                    # Fallback: if watermark fetch fails, leave offset unset
                    new_positions.append(tp)
            if new_positions:
                consumer.assign(new_positions)
            break

    # Now produce N events (memory stores) — only these should be consumed.
    N = 5
    for i in range(N):
        coord = (float(i), float(i + 0.1), float(i + 0.2))
        payload = {"task": f"kafka-flow-{i}", "importance": i + 1}
        memory.store_memory(coord, payload, memory_type=MemoryType.EPISODIC)

    # Poll for events with detailed debug
    received = []
    deadline = time.time() + 25
    while time.time() < deadline and len(received) < N:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            # Ignore partition EOF or benign errors
            continue
        try:
            import json

            evt = json.loads(msg.value())
        except Exception:
            continue
        task = evt.get("payload", {}).get("task", "")
        if task.startswith("kafka-flow-") and evt.get("type") == "created":
            received.append(evt)

    consumer.close()
    # Fallback diagnostic: if none received but WAL empty, surface diagnostic info.
    if len(received) < N:
        # Collect minimal diagnostics
        diag = {
            "bootstrap": bootstrap,
            "effective_namespace": effective_namespace,
            "received": len(received),
        }
        pytest.fail(f"Kafka events missing: {diag}")

    # Basic schema field checks
    field_counter = Counter()
    for e in received:
        for f in ["event_id", "id", "namespace", "type", "timestamp", "payload"]:
            assert f in e
        field_counter.update(e.keys())
        # Assert namespace matches either explicit test namespace or overridden SOMA_NAMESPACE
        assert e["namespace"] in {namespace, effective_namespace}
    # Ensure at least one payload has our highest importance
    assert any(e["payload"].get("importance") == N for e in received)
