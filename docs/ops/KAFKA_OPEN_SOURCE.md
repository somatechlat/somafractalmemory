# Kafka / Kafka-Compatible Operations

SomaFractalMemory ships with a single-node Confluent Kafka broker (previously Redpanda) for event streaming. This guide explains how to run the open-source stack that ships with the repository and how the workers consume events.

---

## Services
| Component | Source | Purpose |
|-----------|--------|---------|
| Kafka broker | `docker-compose.yml` (`kafka`) | Kafka-compatible broker storing `memory.events`. |
| Consumer | `docker-compose.yml` (`somafractalmemory_kube`, profile `consumer`) | Runs `python scripts/run_consumers.py`, subscribing to `memory.events`. |
| Registry (optional) | `docker-compose.dev.yml` (`apicurio`) | Schema registry started via `start_stack.sh --with-broker`. |

---

## Environment Variables
Set inline in `docker-compose.yml` (mirror in `.env` when running locally):
- `KAFKA_BOOTSTRAP_SERVERS` – broker address, defaults to `kafka:9092` inside Docker.
- `KAFKA_MEMORY_EVENTS_TOPIC` – topic used by producers/consumers (`memory.events`).
- `KAFKA_CONSUMER_GROUP` – consumer group id (`soma-consumer-group`).
- `EVENTING_ENABLED` – turn event publishing on/off in the API layer.
- Optional TLS/SASL: `KAFKA_SECURITY_PROTOCOL`, `KAFKA_SSL_CA_LOCATION`, `KAFKA_SASL_*`.

---

## Producing Events
`eventing/producer.py` exposes two helpers:
```python
from eventing.producer import build_memory_event, produce_event

event = build_memory_event(namespace="demo", payload={"example": True})
produce_event(event)  # publishes to memory.events
```
The producer validates each payload against `schemas/memory.event.json` and uses `confluent_kafka`. The API calls this helper automatically when `memory.eventing_enabled` is true.

---

## Consuming Events
`scripts/run_consumers.py` performs the following steps:
1. Create an `AIOKafkaConsumer` subscribed to `memory.events`.
2. For each message:
   - `workers/kv_writer.process_message` upserts the canonical JSON into Postgres via `PostgresKeyValueStore`.
   - `workers/vector_indexer.index_event` generates a deterministic vector and upserts it into Qdrant.
3. Record Prometheus metrics (`consumer_messages_consumed_total`, success/failure counters, latency histograms).
4. Expose metrics on `http://localhost:8001/metrics` (override with `CONSUMER_METRICS_PORT`).

This consumer runs inside the `somafractalmemory_kube` service (profile `consumer`) defined in `docker-compose.yml`. Start it manually with:
```bash
docker compose --profile consumer up -d somafractalmemory_kube
```
Logs are available via `docker compose --profile consumer logs -f somafractalmemory_kube`.

---

## Local Broker with `start_stack.sh`
To run only the messaging layer without the full compose stack:
```bash
./scripts/start_stack.sh evented_enterprise   # starts the docker-compose broker (Kafka; legacy Redpanda if defined)
```
Combine this with a locally running API (e.g., `uvicorn examples.api:app`) after exporting the matching environment variables (such as `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`).

---

## Operational Tips
- The API and consumer depend on the same environment variables; edit them together in `docker-compose.yml` and keep `.env` in sync for local CLI/tests.
- If you disable eventing (`EVENTING_ENABLED=false`), you may also stop the `somafractalmemory_kube` service to save resources.
- When running outside Docker, install `confluent-kafka` and `aiokafka` locally and adjust `KAFKA_BOOTSTRAP_SERVERS` accordingly.
- For TLS/SASL clusters, populate the corresponding environment variables. The producer and consumer pass them straight to `confluent_kafka`/`aiokafka`.

---

*Return to `docs/CANONICAL_DOCUMENTATION.md` for broader operational guidance, or `docs/api.md` for application-facing endpoints.*
