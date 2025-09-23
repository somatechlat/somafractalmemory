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

import asyncio
import json
import logging
import os
from typing import Any, Dict

from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Histogram, start_http_server

from workers.kv_writer import process_message
from workers.vector_indexer import index_event

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
# Configuration (environment variables – fall back to dev defaults)
# ---------------------------------------------------------------------------
BROKER_URL = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_MEMORY_EVENTS_TOPIC", "memory.events")
GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP", "soma-consumer-group")
METRICS_PORT = int(os.getenv("CONSUMER_METRICS_PORT", "8001"))

log = logging.getLogger(__name__)


async def consume() -> None:
    """Consume messages indefinitely.

    Each record is expected to be a JSON‑encoded object that conforms to the
    ``memory.event`` schema. Errors are logged and counted, but the loop keeps
    running so that a single bad message does not halt the pipeline.
    """
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=BROKER_URL,
        group_id=GROUP_ID,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            MESSAGES_CONSUMED.labels(topic=TOPIC).inc()
            record: Dict[str, Any] = msg.value
            with PROCESS_LATENCY.labels(component="kv_writer").time():
                ok_kv = process_message(record)
            with PROCESS_LATENCY.labels(component="vector_indexer").time():
                ok_vec = index_event(record)
            if ok_kv and ok_vec:
                PROCESS_SUCCESS.labels(component="both").inc()
                log.info("Successfully processed event %s", record.get("event_id"))
            else:
                # Count failures per component for easier debugging
                if not ok_kv:
                    PROCESS_FAILURE.labels(component="kv_writer").inc()
                if not ok_vec:
                    PROCESS_FAILURE.labels(component="vector_indexer").inc()
                log.warning("Processing failed for event %s", record.get("event_id"))
    finally:
        await consumer.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Expose Prometheus metrics endpoint
    start_http_server(METRICS_PORT)
    log.info("Prometheus metrics exposed on http://localhost:%s/metrics", METRICS_PORT)
    # Run the consumer loop
    asyncio.run(consume())


if __name__ == "__main__":
    main()
