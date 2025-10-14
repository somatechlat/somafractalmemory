"""Run the KV writer and vector indexer consumers.

This script connects to the Redpanda/Kafka broker (using aiokafka) and
consumes messages from the ``memory.events`` topic. For each event it:

1. Calls ``kv_writer.process_message`` to upsert the canonical JSON record
    into PostgreSQL.
2. Calls ``vector_indexer.index_event`` to generate a deterministic vector
    and upsert it into Qdrant.

Prometheus metrics are exposed on ``localhost:8001/metrics`` so that the
consumer health can be monitored.
"""

# Ensure the repository root is on sys.path so `from common...` imports work
# when the script is executed inside a container or directly from source.
import os
import sys
from typing import Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Standard library
import asyncio
import json
import ssl

# Third-party
from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Histogram, start_http_server

# Local
from common.config.settings import load_settings
from common.utils.logger import configure_logging

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
MESSAGES_CONSUMED = Counter(
    "consumer_messages_consumed_total",
    "Total number of messages consumed from the Kafka topic",
    ["topic"],
)
PROCESS_SUCCESS = Counter(
    "consumer_process_success_total",
    "Number of successfully processed messages (both DB and vector)",
    ["component"],
)
PROCESS_FAILURE = Counter(
    "consumer_process_failure_total",
    "Number of failed processing attempts",
    ["component"],
)
PROCESS_LATENCY = Histogram(
    "consumer_processing_latency_seconds",
    "Time taken to process a single message",
    ["component"],
)

# ---------------------------------------------------------------------------
# Configuration (environment variables – fall back to centralized settings or dev defaults)
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

log = configure_logging(
    "somafractalmemory-consumer",
    level=LOG_LEVEL,
).bind(component="consumer")

_settings = load_settings()
BROKER_URL = os.getenv("KAFKA_BOOTSTRAP_SERVERS") or f"{_settings.infra.kafka}:9092"
TOPIC = os.getenv("KAFKA_MEMORY_EVENTS_TOPIC", "memory.events")
GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP", "soma-consumer-group")
METRICS_PORT = int(os.getenv("CONSUMER_METRICS_PORT", "8001"))


async def consume() -> None:
    """Consume messages indefinitely.

    Each record is expected to be a JSON‑encoded object that conforms to the
    ``memory.event`` schema. Errors are logged and counted, but the loop keeps
    running so that a single bad message does not halt the pipeline.
    """
    # Import project-local modules lazily so this file can be imported without
    # needing the repository path to be preconfigured. This avoids executing
    # module-level statements before imports (ruff/flake8 E402).
    from workers.kv_writer import process_message
    from workers.vector_indexer import index_event

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=BROKER_URL,
        group_id=GROUP_ID,
        enable_auto_commit=False,
        # Decode JSON values into Python dicts
        value_deserializer=lambda v: (
            json.loads(v.decode("utf-8"))
            if isinstance(v, (bytes | bytearray))
            else (v if isinstance(v, dict) else json.loads(v))
        ),
        # TLS/SSL configuration
        security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
        ssl_context=(
            ssl.create_default_context(cafile=os.getenv("KAFKA_SSL_CA_LOCATION"))
            if os.getenv("KAFKA_SSL_CA_LOCATION")
            else None
        ),
        # SASL configuration (plain mechanism as example)
        sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
        sasl_plain_username=os.getenv("KAFKA_SASL_USERNAME"),
        sasl_plain_password=os.getenv("KAFKA_SASL_PASSWORD"),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            MESSAGES_CONSUMED.labels(topic=TOPIC).inc()
            record: dict[str, Any] = msg.value if isinstance(msg.value, dict) else {}
            if not record:
                try:
                    record = json.loads(msg.value)
                except Exception:
                    log.warning(
                        "Skipping non-JSON message",
                        value=repr(msg.value),
                    )
                    continue
            with PROCESS_LATENCY.labels(component="kv_writer").time():
                ok_kv = process_message(record)
            with PROCESS_LATENCY.labels(component="vector_indexer").time():
                ok_vec = index_event(record)
            if ok_kv and ok_vec:
                PROCESS_SUCCESS.labels(component="both").inc()
                log.info("Successfully processed event", event_id=record.get("event_id"))
            else:
                # Count failures per component for easier debugging
                if not ok_kv:
                    PROCESS_FAILURE.labels(component="kv_writer").inc()
                if not ok_vec:
                    PROCESS_FAILURE.labels(component="vector_indexer").inc()
                log.warning(
                    "Processing failed for event",
                    event_id=record.get("event_id"),
                )
    finally:
        await consumer.stop()


def main() -> None:
    # Expose Prometheus metrics endpoint
    # Ensure the repository root (project root) is on the import path when
    # the script is executed (only required when running from source).
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    start_http_server(METRICS_PORT)
    log.info(
        "Prometheus metrics exposed",
        host="localhost",
        port=METRICS_PORT,
        endpoint="/metrics",
    )
    # Log broker URL for debugging
    log.info("Broker configuration", broker_url=BROKER_URL)
    # Run the consumer loop
    asyncio.run(consume())


if __name__ == "__main__":
    main()
