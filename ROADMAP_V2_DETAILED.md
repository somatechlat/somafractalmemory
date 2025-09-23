# SomaFractalMemory — V2 Detailed Roadmap

Last updated: 2025-09-23

This document is a single, detailed roadmap for the v2 effort. It merges the existing high-level `ROADMAP_V2.md` direction with the latest engineering decisions (JSON-only serialization, open-source messaging stack), acceptance criteria, measurable objectives, math/metrics for correctness, and an ordered implementation plan with concrete artifacts.

Goals (concise)
- Safety-first: JSON-only payloads (no runtime reading/writing of Python pickles).
- Evented architecture: durable, auditable event streams and canonical JSONB storage.
- Scalable: allow horizontal scale for producers and consumers; low-latency reads via Redis cache.
- Observable & auditable: metrics, tracing, and replayable events for reconstruction.
- Reproducible math: define decay and scoring functions with tests and deterministic behavior for CI.

Summary of recent status (baseline)
- Central serializer (`somafractalmemory/serialization.py`) updated to JSON-first and raises on non-JSON input. (Done)
- Docs updated: `docs/CONFIGURATION.md` updated to assert JSON-only policy. (Done)
- Generated site artifacts adjusted in-place to reflect JSON-only docs (temporary; canonical rebuild via mkdocs recommended). (Temporarily done)
- Roadmap and internal comments edited to avoid explicit 'pickle' references and to assert JSON-first policy. (Done)
- A focused unit test (`tests/test_wal_reconcile.py`) was run successfully; full test suite not yet executed. (Partial)

Requirements contract (v2 acceptance criteria)
- Functional contract
  - Input: store/retrieve API calls with JSON-compatible `payload` objects and optional fields (embedding array optional, importance numeric, timestamp iso8601 or epoch).
  - Output: on `store()` the system publishes a validated JSON event to `memory.events` and returns a stable `id`.
  - Consumer outputs: durable JSONB rows in Postgres (canonical store) and upserts into vector index (Qdrant) with consistent IDs.
  - No code path should write or read Python pickle blobs in production runtime (v2 enforcement point: `serialization.deserialize()` raises on non-JSON).

- Non-functional contract
  - Latency: median read (cache hit) < 5 ms on typical dev hardware; median write (API ack after produce) < 30 ms (producer ack depends on broker configuration). Targets are adjustable by deployment class.
  - Throughput: baseline single-node test: 2k events/s sustained with batching (tunable via partition count and producer batching); plan for horizontal scaling.
  - Durability: events persisted and replicated across Kafka brokers with replication factor >= 3 in production; compacted topic for `memory.latest`.
  - Observability: end-to-end traceable event IDs, consumer lag metrics, and DLQ visibility.

Mathematical contracts and scoring (deterministic, testable)

1) Decay and scoring functions (used for pruning and prioritization)

Define memory score S as:

  S = w_age * f_age(age_hours) + w_recency * f_recency(recency_hours) + w_access * f_access(access_count) - w_importance * importance

Where:
- age_hours := now_hours - creation_hours
- recency_hours := now_hours - last_access_hours
- access_count := integer >= 0
- importance := positive float where larger means more important
- w_* are tunable weights (floats)

Recommended functional forms (deterministic and differentiable where possible):
- f_age(t) = log(1 + t)  (sub-linear growth with age)
- f_recency(t) = 1 / (1 + t)  (recency reward decaying with time)
- f_access(n) = 1 / (1 + exp(-(n - 1)))  (sigmoid to saturate at high access)

Default weights (initial): w_age=1.0, w_recency=1.0, w_access=0.5, w_importance=2.0

Acceptance rule for pruning (example): prune when S > threshold_prune (default 2.0). These formulas are unit-testable: provide synthetic inputs and assert deterministic outputs.

2) Idempotency and exactly-once design
- All events include `event_id` (uuid) and `id` (memory id). Consumers must check the `processed_event_ids` index or use Postgres upserts by `id` plus `last_event_id` to guarantee idempotent commits.
- Use upsert semantics in Postgres: INSERT ... ON CONFLICT(id) DO UPDATE SET payload = EXCLUDED.payload, last_event_id = EXCLUDED.event_id ...

Event & data contracts (JSON Schema canonical example)

memory.created / memory.updated (JSON Schema snippet):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "memory.event",
  "type": "object",
  "required": ["event_id","id","namespace","type","timestamp","payload"],
  "properties": {
    "event_id": {"type":"string","format":"uuid"},
    "id": {"type":"string","format":"uuid"},
    "namespace": {"type":"string"},
    "type": {"type":"string","enum":["created","updated","deleted"]},
    "timestamp": {"type":"string","format":"date-time"},
    "payload": {"type":"object"},
    "importance": {"type":"number"},
    "embedding": {"type":"array","items":{"type":"number"}},
    "model_revision": {"type":"string"}
  }
}
```

Store this schema in Apicurio or Karapace (open-source registry) for validation at produce time.

Infrastructure choices (open-source only)
- Broker: Apache Kafka (KRaft mode) or Redpanda for local/dev convenience.
- Schema registry: Apicurio Registry or Karapace (pick one and document usage).
- Connect: Kafka Connect (community) with JDBC Sink connector for Postgres JSONB writes.
- Operator: Strimzi (Kubernetes) for production on K8s; `docker-compose.dev.yml` for local dev with Redpanda + Apicurio.
- Clients: `confluent-kafka` (librdkafka) or `aiokafka` (pure Python) for producers/consumers; `jsonschema` for local validation during tests.

Phased implementation plan (ordered, with measurable milestones)

Phase 0 — Safety & foundations (week 0-1)
- What
  - Enforce JSON-only serialization centrally (`serialization.py`) and ensure any deserialize() raises on non-JSON.
  - Update docs and config (done partially).
  - Add CI check: a unit test that tries to deserialize a non-JSON blob and asserts ValueError.
- Acceptance
  - `serialization.deserialize(b'not-json')` raises ValueError.
  - Documentation updated; mkdocs build successful (docs canonicalized).

Phase 1 — Event model & local dev stack (week 1-2)
- What
  - Add `eventing/producer.py` with JSON Schema validation against local schema files.
  - Provide `docker-compose.dev.yml` with Redpanda (or Kafka KRaft), Apicurio/Karapace, Kafka Connect (JDBC sink), Postgres, Qdrant (or InMemoryVectorStore), and a small `kcat` image for debugging.
  - Create initial topics: `memory.events` (compacted), `memory.audit` (append-only), `embedding.requests`, `embedding.responses`, `memory.dlq`.
- Acceptance
  - `docker-compose.dev.yml` brings up the stack and `producer.py` can produce a valid `memory.created` event; Connect writes to Postgres (row appears in canonical table) within 5s.

Phase 2 — Consumers & vector indexing (week 2-3)
- What
  - Implement `workers/kv_writer.py` consumer skeleton using consumer-library and Postgres upserts.
  - Implement `workers/vector_indexer.py` consumer: accepts events, optionally requests embeddings (internal or external call), and upserts vectors to Qdrant.
  - Implement DLQ behavior and retries.
- Acceptance
  - Messages produced by `producer.py` are visible in Postgres via `kv_writer` and vectors appear in Qdrant for 95% of produced events in local tests.

Phase 3 — Schema governance & CI (week 3-4)
- What
  - Configure Apicurio/Karapace with compatibility rules (backward compatible by default) and add CI check to validate that changed schemas are compatible.
  - Add unit tests for schema validation and consumer idempotency.
- Acceptance
  - CI fails on schema-incompatible commits and consumer tests pass.

Phase 4 — Enterprise features: evented pipeline, dual-write optionality, cutover plan (weeks 4-8)
- What
  - Add eventing producers from the API in `somafractalmemory/core.py` (or `eventing/producer.py`) and ensure `create_memory_system()` wiring supports `EVENTED_ENTERPRISE` mode.
  - Implement dual-write (optional) and flag-based cutovers.
  - Add monitoring (Prometheus metrics, Grafana dashboards) for broker metrics and consumer lag.
- Acceptance
  - Production-like dual-write smoke test (write through API with `SOMA_DUAL_WRITE=true`) shows parity between legacy and new flows for a 1-hour synthetic workload with <1% divergence.

Phase 5 — Hardening & production readiness (weeks 8-12)
- What
  - Run integrated load tests, establish SLOs (latency, availability), backup/restore docs, runbook for schema migrations and cutovers.
  - Implement role-based access, TLS, SASL for brokers, and secure schema registry.
- Acceptance
  - Load test passes defined SLOs; runbook validated by team drill; TLS and auth configured.

Quality gates & verification (applies to each phase)
- Build: `python -m pip install -r requirements.txt` (or equivalent venv); project imports cleanly.
- Lint/Typecheck: run `ruff/black` and `mypy` as configured in repo.
- Unit tests: run `pytest -q` (all tests must pass for merging to main branch). New tests added for serializer, schema validation, and consumer idempotency.
- Smoke tests: `docker-compose.dev.yml` up with minimal producer/consumer integration smoke tests.

Metrics & monitoring (concrete math & thresholds)
- Consumer lag (L): alert when L > 1000 messages OR sustained >1 minute.
- Event processing time (T_proc): measure time between broker commit and successful Postgres upsert for an event; SLO: p95(T_proc) < 500ms in production.
- Decay correctness tests: add unit tests that assert monotonicity and bounds of `f_age`, `f_recency` and overall score S.

Risk analysis & mitigations
- Risk: schema mismatch breaks consumers. Mitigation: use Schema Registry (Apicurio) and CI compatibility checks; provide a staging-compatible schema promotion workflow.
- Risk: large payloads bloat Kafka. Mitigation: store large artifacts in object store and publish references.
- Risk: operational complexity of Kafka. Mitigation: start with Redpanda for prototyping and Strimzi/KRaft for production; document runbook.

Repository changes recommended (minimum)
- Add `eventing/producer.py`, `workers/kv_writer.py`, `workers/vector_indexer.py` (skeletons + tests).
- Add `docker-compose.dev.yml` for local dev stack (Redpanda + Apicurio + Connect + Postgres + Qdrant).
- Add `docs/ops/KAFKA_OPEN_SOURCE.md` describing the chosen open-source stack, runbook, and step-by-step cutover plan.
- Add `ROADMAP_V2_DETAILED.md` (this file) and link it from `ROADMAP_V2.md` and `docs/`.

Current-status mapping (quick)
- serialization.py — updated to JSON-first: DONE
- docs/CONFIGURATION.md — JSON-only policy: DONE
- site/ (generated) — edited in-place but should be rebuilt: TODO (rebuild docs site)
- ROADMAP_V2.md — high-level roadmap present: MERGED (this file expands it)
- tests — currently a focused test run passed; full test suite: TODO (run full pytest)

Concrete next steps I can execute now (pick any):
1) Create `docker-compose.dev.yml` for a local open-source dev stack and add skeleton producer/consumers + tests. (Medium work)
2) Add `docs/ops/KAFKA_OPEN_SOURCE.md` and update `config.example.yaml` with Kafka/Apicurio entries. (Small)
3) Add unit tests and CI checks for serializer and schema validation and run full test suite. (Small-Medium)

If you want me to start implementing any of the above, tell me which of 1/2/3 and I will:
- mark the corresponding todo as in-progress,
- add files and tests,
- run quick validation locally (where possible), and
- report back with results and suggested follow-ups.

---

Appendix: Minimal developer commands (local dev)

Start dev stack (when `docker-compose.dev.yml` added):

```bash
# from repo root
docker compose -f docker-compose.dev.yml up --build
# in another shell: run producer smoke test
python -m examples.produce_sample_event
```

Test examples (unit tests):

```bash
# run unit tests
.venv/bin/python -m pytest -q
```
