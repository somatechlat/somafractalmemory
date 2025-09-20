SomaFractalMemory — Architecture
================================

This document describes the overall architecture, components, and dataflows for SomaFractalMemory.

High-level components

1. API / CLI layer
   - `examples/api.py` or the enterprise API (FastAPI) exposes HTTP endpoints for store, recall, link, and health checks.
   - `cli.py` provides a command-line wrapper for the same functionality.

2. Core memory engine (`SomaFractalMemoryEnterprise`)
   - Responsible for serialization, metadata, hooks, eviction/decay, WAL reconciliation, and orchestration between subcomponents.

3. Key-Value store (KV)
   - Pluggable (Redis-backed in production, FakeRedis in tests).
   - Stores JSON-serialized memory payloads plus meta hashes (creation timestamp, last_accessed_timestamp).

4. Vector store (embeddings)
   - Pluggable vector engine (in-memory for ON_DEMAND, Qdrant for LOCAL_AGENT/ENTERPRISE).
   - Responsible for upserts, searches, and vector scrolls for batching/repairs.

5. Graph store
   - NetworkX-based in-memory graph by default. Supports `add_link` and `find_shortest_path`.

6. Prediction provider
   - Optional integration that can enrich memories with predictions and confidence values.

Data flows

- Store path:
  1. Caller invokes `store_memory`.
  2. Core serializes payload (JSON-first, optional Pickle fallback) and writes to KV.
  3. Core computes embedding (HF or fallback hash) and upserts into vector store.
  4. Core updates eviction index (zset) with computed score.
  5. Core optionally creates WAL item if vector upsert fails.

- Recall path:
  1. Caller invokes `recall` with text query.
  2. Core converts query to embedding and queries vector store.
  3. Results are filtered by memory type and optionally scored with context.
  4. For `retrieve` (by coordinate), core updates access_count and last_accessed metadata and refreshes eviction index.

Eviction index

- Implemented as a KV-backed sorted set containing data_key members. The score is computed by `_compute_eviction_score` and updated on store, retrieve, and decay.
- A scheduled pruning thread (`_decay_memories`) recomputes scores and prunes or reduces payload size for items above decay thresholds.

Observability & metrics

- Metrics are low-cardinality and registered to the default Prometheus registry by default.
- The code exposes counters/histograms/gauges for store/recall/upserts/eviction and WAL backlog.

Operational concerns

- Serialization safety: default JSON; pickle opt-in.
- HF model downloads: opt-in/unpinned downloads require environment flags.
- Tests use FakeRedis and in-memory vector store to provide fast CI feedback.
