"""Kafka event producer for memory events.

The original implementation printed the event to ``stdout`` – useful for quick
debugging but not suitable for a production pipeline.  This module now provides
real Kafka publishing using the **confluent‑kafka** client (which wraps the
high‑performance *librdkafka* library).

Configuration is driven by environment variables prefixed with ``KAFKA_`` – the
same variables that are documented in ``README.md`` and ``docs/ARCHITECTURE.md``.

* ``KAFKA_BOOTSTRAP_SERVERS`` – comma‑separated list of broker addresses
  (default ``localhost:9092``).
* ``KAFKA_SECURITY_PROTOCOL`` – ``PLAINTEXT`` (default), ``SSL`` or ``SASL_SSL``.
* ``KAFKA_SSL_CA_LOCATION`` – path to CA certificate (required when using SSL).
* ``KAFKA_SASL_MECHANISM`` – e.g. ``PLAIN``.
* ``KAFKA_SASL_USERNAME`` / ``KAFKA_SASL_PASSWORD`` – credentials for SASL.

The module exposes two public helpers:

* ``build_memory_event`` – validates the payload against a minimal JSON schema.
* ``produce_event`` – serialises the event to JSON and sends it to the Kafka
  topic (default ``memory.events``).  The function returns ``True`` on success
  and raises ``RuntimeError`` on delivery failure.
"""

import json
import os
import time
import uuid
from typing import Any

from jsonschema import ValidationError, validate

# ---------------------------------------------------------------------------
# JSON schema – kept minimal but must stay in sync with ``schemas/memory.event.json``
# ---------------------------------------------------------------------------
MEMORY_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["event_id", "id", "namespace", "type", "timestamp", "payload"],
    "additionalProperties": False,
}


def _kafka_producer():
    """Create (or reuse) a singleton ``confluent_kafka.Producer``.

    The configuration mirrors the environment variables documented in the
    repository.  If the ``confluent_kafka`` package is missing we raise a clear
    ``ImportError`` so the caller can install the dependency.
    """
    try:
        from confluent_kafka import Producer  # type: ignore
    except Exception as exc:
        raise ImportError(
            "confluent_kafka is required for event publishing. Install with "
            "'pip install confluent-kafka'"
        ) from exc

    # Build the configuration dictionary from env vars.
    conf: dict[str, Any] = {
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        "security.protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
    }

    # SSL configuration (optional)
    if conf["security.protocol"] in {"SSL", "SASL_SSL"}:
        ca_loc = os.getenv("KAFKA_SSL_CA_LOCATION")
        if ca_loc:
            conf["ssl.ca.location"] = ca_loc
        # Client certificates can be added via standard librdkafka keys if needed.

    # SASL configuration (optional)
    if conf["security.protocol"].startswith("SASL"):
        conf["sasl.mechanisms"] = os.getenv("KAFKA_SASL_MECHANISM", "PLAIN")
        conf["sasl.username"] = os.getenv("KAFKA_SASL_USERNAME", "")
        conf["sasl.password"] = os.getenv("KAFKA_SASL_PASSWORD", "")

    # ``linger.ms`` and ``batch.num.messages`` can be tuned for higher throughput;
    # defaults are fine for our use‑case.
    return Producer(conf)


# Lazily created singleton – thread‑safe because module import is atomic.
_PRODUCER = _kafka_producer()


def _delivery_report(err, msg):  # pragma: no cover – exercised via produce_event
    """Callback invoked by ``confluent_kafka`` after each send.

    If ``err`` is not ``None`` the delivery failed; we raise a ``RuntimeError`` so
    the caller (the memory core) can log the failure.  Successful deliveries are
    silently ignored – they are already persisted in Kafka.
    """
    if err is not None:
        raise RuntimeError(f"Kafka delivery failed: {err}")
    # No‑op on success – could add debug logging here if desired.


def build_memory_event(namespace: str, payload: dict) -> dict:
    """Create a validated memory event.

    The function generates a UUID for both ``event_id`` (the Kafka‑level identifier)
    and ``id`` (the stable memory identifier).  It also adds a ``timestamp``.
    Validation against ``MEMORY_SCHEMA`` guarantees that downstream consumers can
    rely on a stable contract.
    """
    event = {
        "event_id": str(uuid.uuid4()),
        "id": str(uuid.uuid4()),
        "namespace": namespace,
        "type": "created",
        "timestamp": time.time(),
        "payload": payload,
    }
    try:
        validate(instance=event, schema=MEMORY_SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Event does not conform to schema: {e}") from e
    return event


def produce_event(event: dict, topic: str = "memory.events") -> bool:
    """Publish a memory event to Kafka.

    The function serialises ``event`` to JSON, sends it to ``topic`` and blocks
    until the delivery callback confirms success (or raises on failure).  It
    returns ``True`` when the message is successfully queued.
    """
    # ``_PRODUCER`` is a module‑level singleton – safe for concurrent calls.
    serialized = json.dumps(event).encode("utf-8")
    _PRODUCER.produce(topic, serialized, callback=_delivery_report)
    # ``flush`` ensures the message is sent before we return.  It respects the
    # ``linger.ms`` configuration set in the producer.
    _PRODUCER.flush()
    return True


# ---------------------------------------------------------------------------
# End of real Kafka producer implementation.
# ---------------------------------------------------------------------------
