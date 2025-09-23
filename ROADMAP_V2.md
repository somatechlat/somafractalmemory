# SomaFractalMemory — V2 Roadmap & Architecture

This document is the canonical V2 plan for developers and automated agents. It describes goals, modes, architecture, data contracts, implementation milestones, and the immediate next steps to start development on branch `v2.0`.

## Vision

Make SomaFractalMemory the fastest, safest, and most production-ready memory manager. Key pillars:
- Safety: no insecure serialization (no pickle in production), input validation, and auditability.
- Scalability: event-driven architecture (Kafka) for high-throughput durability and replay.
- Performance: low-latency reads (Redis cache + Qdrant), batched vector indexing, and optimized embeddings.
- Mathematical purity: keep core algorithms pure and testable (no IO), preserve `MinimalSoma` for research.

## Modes (runtime)

1. DEVELOPMENT (default)
   - Local developer workflow using Redis + local Qdrant.
   - Synchronous store/recall for fast feedback.
   - Optional `SOMA_DUAL_WRITE=true` to produce events for parity testing.

2. TEST
   - CI/Unit test mode with deterministic in-memory components (fakeredis, InMemoryVectorStore).
   - Deterministic embedding fallback for reproducible tests.

3. EVENTED_ENTERPRISE
   - Production event-driven mode: Kafka (memory.events) + Postgres (canonical JSONB) + Qdrant (vectors) + Redis (cache/locks).
   - API publishes typed events; consumers (KVWriter, VectorIndexer, GraphUpdater) perform durable writes and indexing asynchronously.

4. CLOUD_MANAGED
   - Alias of EVENTED_ENTERPRISE for managed services (Confluent/AWS MSK, RDS/Aurora, Qdrant Cloud).

5. LEGACY_COMPAT (hidden/opt-in)
   - Temporary compatibility mode (not enabled by default). Avoid in new deployments.

## Components

- API (FastAPI): validates requests, serializes events, and publishes to Kafka (or performs sync writes in DEVELOPMENT).
- Kafka: durable event bus for memory.events (Avro/JSON Schema) and embedding requests/responses.
- Postgres: canonical JSONB store for memory records, audit, and queries.
- Qdrant: vector index with payload pointing to Postgres IDs.
- Redis: cache, locks, expirations, rate-limits.
- Embedding Service: scalable, model-pinned service (HTTP or Kafka backed).
- Graph DB: Neo4j / JanusGraph for semantic links and graph queries.

## Data contracts and event schema (example)

- memory.created / memory.updated (JSON)
  - id: uuid
  - namespace: string
  - coordinate: [float...]
  - payload: object (JSON-compatible)
  - memory_type: "episodic" | "semantic"
  - timestamp: epoch
  - importance: int
  - embedding: optional [float...] (if precomputed)
  - model_revision: optional string

Use JSON Schema or Avro for schema enforcement and evolution.

## File-level plan (what we'll add/change in v2.0)

- (Removed) legacy binary Python serialization migration helpers: legacy binary Python serialization migration is not required for this deployment.

## High-level roadmap & milestones

Phase 0 — Safety & foundation (1 week)
- JSON-first serialization (no pickle writes).
- Developer-focused `DEVELOPMENT` mode.

Phase 1 — Local evented dev infra (1 week)
- Add Kafka & Postgres to docker-compose.dev (optional start).
- Implement producer wrapper & simple KV writer consumer.

Phase 2 — Dual-write + Vector Indexer (2 weeks)
- Dual-write option for parity; implement VectorIndexer to call embedding service and batch-upsert to Qdrant.

Phase 3 — Switch reads & Cutover (2 weeks)
- Reads prefer Postgres + Redis cache; remove legacy synchronous Qdrant writes.

Phase 4 — Kubernetes & production hardening (3-6 weeks)
- Helm charts, operators, autoscale, tracing, monitoring, security.

## Immediate next steps (I'll start these now)

1. Add `serialization.py` (JSON-first) and wire `core.store()` and `core.retrieve()` to use it (safe, non-destructive).
2. Update `factory.py` to the new `MemoryMode` enum with `DEVELOPMENT`, `TEST`, `EVENTED_ENTERPRISE`, `CLOUD_MANAGED`, and `LEGACY_COMPAT`.
3. Create branch `v2.0` (already done) and commit changes there.

## Developer checklist

- Set `SOMA_MODE=DEVELOPMENT` locally.
- Use `docker-compose.dev.yml` (TBD) to start Redis + Qdrant + local embedding.
- For event testing, start Kafka & Postgres with `docker-compose.dev-full.yml`.

## Acceptance criteria for phase 0

- `core.store()` writes JSON payloads to KV store (no new pickle writes).
- Tests covering serializer pass.
- Developer mode behaves as before for local tests, with JSON payloads.

---

This file is authoritative for branch `v2.0`. Further design artifacts (diagrams, prod manifests, and worker implementations) will be added under `docs/` and `somafractalmemory/eventing/` during the following phases.
