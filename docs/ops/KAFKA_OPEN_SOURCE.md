# Open-source eventing stack for SomaFractalMemory (v2)

This document describes the recommended open-source-only messaging and schema stack for v2, with operational notes and a short cutover/runbook.

## Recommended components

- Broker: Apache Kafka (KRaft mode) for production. For local development, use Redpanda (lightweight and drop-in compatible).
- Schema registry: Apicurio Registry or Karapace (choose one). Store JSON Schema artifacts for `memory.event` and other topics.
- Operators and orchestration:
  - Strimzi for Kubernetes (production deployments).
  - `docker-compose.dev.yml` for local development with Redpanda + Apicurio.
- Connectors: Kafka Connect (community) with the JDBC Sink for writing JSONB rows to Postgres.
- Consumers:
  - `workers/kv_writer.py` (Postgres consumer/upserter)
  - `workers/vector_indexer.py` (embedding + Qdrant upserts)
- Clients: `confluent-kafka` (librdkafka) or `aiokafka` (async) in Python.

## Topic design

- `memory.events` (compact if desired / or partitioned with compaction for `memory.latest`)
- `memory.audit` (append-only)
- `embedding.requests`, `embedding.responses`
- `memory.dlq`

## Schema governance

- Use JSON Schema stored in the registry; require `event_id` and `id` fields.
- Set compatibility rules (backward-compatible by default). Changes to schemas must be accompanied by CI compatibility checks.

## Local development compose (high level)

A `docker-compose.dev.yml` should include:
- redpanda (or kafka image in KRaft mode)
- apicurio or karapace
- postgres
- qdrant (or a lightweight stand-in)
- connect (kafka-connect) with JDBC sink
- kafka UI (optional)

## Cutover/runbook (high-level)

1. Stand up the registry (Apicurio) and import schemas.
2. Start consumers in a staging environment and set `DRAIN_OLD_EVENTS=false`.
3. Enable producer dual-write (legacy + new eventing) and run synthetic traffic; compare Postgres rows until parity is established.
4. Switch consumers to read-only mode from legacy store, monitor for discrepancies, then cut over traffic routing.
5. Decommission legacy write path after verification.

## Notes

- Keep all event payloads JSON-first. Do not allow pickle serialization anywhere in eventing code.
- Implement idempotency via `event_id` tracking and Postgres `upsert` semantics.
- Add metrics for producer latency, consumer processing time, and consumer lag.
