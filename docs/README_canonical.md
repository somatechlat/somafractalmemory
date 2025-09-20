SomaFractalMemory — Canonical Specification
==========================================

This document is the canonical, technical specification for the SomaFractalMemory component
used inside the SOMABRAin platform. It is intended for architects, integrators, and engineers
who want a precise view of the design, interfaces, and operational requirements.

1. Purpose and Scope
--------------------
SomaFractalMemory provides a hybrid memory engine with the following capabilities:
- Persistent/semi-persistent storage of memory payloads (JSON-first).
- Vector embeddings for semantic search (pluggable vector backend).
- A graph layer for explicit relationships and traversal.
- Eviction/decay of memory content based on a tunable, auditable scoring function.
- Observability hooks for Prometheus and optional tracing integrations.

2. Data model (Memory Schema)
-----------------------------
Each memory is stored as a dictionary-like payload with the following canonical fields:
- `coordinate`: list[float] — unique coordinate used as the primary key in the system.
- `memory_type`: str — either `episodic` or `semantic` (see `MemoryType` enum).
- `timestamp`: float — UNIX epoch seconds when the memory was created (added for episodic memories).
- `importance`: int — higher numbers reduce eviction probability.
- `access_count`: int — incremented on retrieval and used to compute eviction score.
- `last_accessed_timestamp`: float — epoch seconds of the last retrieval.
- `predicted_outcome`, `predicted_confidence` — optional fields populated by a prediction provider.

Other application-specific keys may be present and are stored verbatim.

3. Key design APIs
------------------
The primary class is `SomaFractalMemoryEnterprise`, constructed via `create_memory_system`.
Key public methods include:
- `store_memory(coordinate, value, memory_type)` — store or upsert a memory.
- `retrieve(coordinate)` — read a single memory and update access metadata.
- `recall(query, top_k, memory_type)` — semantic recall using vector search with optional
  hybrid context.
- `link_memories(from_coord, to_coord, link_type)` — create a relationship in the graph store.
- `find_shortest_path(from_coord, to_coord)` — graph-based path search.

4. Eviction & decay algorithm
-----------------------------
Eviction score:

```
score = (age_weight * age_hours)
      + (recency_weight * recency_hours)
      - (access_weight * access_count)
      - (importance_weight * importance)
```

- `age_hours` is the number of hours since the creation timestamp.
- `recency_hours` is the number of hours since `last_accessed_timestamp` (or creation time if never accessed).
- `access_count` and `importance` reduce the score; higher importance protects a memory.

When the number of entries tracked by the eviction index exceeds `SOMA_MAX_MEMORY_SIZE`, the
engine removes the highest-score entries (those most eligible for removal). The sorted set
(`eviction_index`) stores members keyed by `namespace:coord_str:data` with the score as the
zset score.

5. Serialization & safety
-------------------------
- Default: JSON serialization and deserialization via `json.loads`/`json.dumps`.
- Optional fallback: Pickle serialization/deserialization when `SOMA_ALLOW_PICKLE=true`.
  This option is dangerous with untrusted data and must only be used in controlled environments.

6. Embeddings & providers
-------------------------
- By default, a deterministic `blake2b`-based fallback produces a fixed-length L2-normalized
  vector if HF transformers are not available.
- If `SOMA_MODEL_REV` is set, the HF model (specified by `SOMA_MODEL_NAME`) is loaded at that
  revision. Unpinned downloads are only allowed if `SOMA_ALLOW_UNPINNED_HF=true`.

7. Observability: Prometheus metrics (precise)
---------------------------------------------
All metrics are registered to the default Prometheus registry. Metric names and types:

- `soma_memory_store_total{namespace}` (Counter): number of successful store operations.
- `soma_memory_recall_total{namespace}` (Counter): number of successful recalls.
- `soma_memory_store_latency_seconds{namespace}` (Histogram): latency of store operations.
- `soma_memory_recall_latency_seconds{namespace}` (Histogram): latency of recall operations.
- `soma_vector_upsert_total{namespace}` (Counter): number of vector upserts made to the vector store.
- `soma_eviction_pruned_total` (Counter): times the engine pruned memories due to eviction.
- `soma_eviction_index_size{namespace}` (Gauge): current length of the eviction index zset.
- `soma_wal_entries_pending{namespace}` (Gauge): pending WAL entries awaiting reconciliation.

8. Operational notes
--------------------
- To expose metrics in a standalone process, call:

```python
from prometheus_client import start_http_server
start_http_server(8000)
```

- Tune `SOMA_MAX_MEMORY_SIZE` and decay weights to balance memory retention vs storage costs.
- For high-throughput environments, ensure the KV and vector backends are provisioned and the
  vector upsert path is decoupled or batched if necessary.

9. Testing & CI
---------------
- The repository contains a comprehensive test suite under `tests/` that exercises store,
  recall, WAL reconciliation, eviction, and providers. Run via `pytest tests/`.

10. Security considerations
---------------------------
- Pickle usage is gated behind an environment flag. Avoid enabling it for any public-facing
  or multi-tenant deployments.
- HF model downloads are opt-in to avoid unexpected network activity.
- Narrow exception handling and timeouts are preferred to avoid catching unrelated errors.

11. Integration with SOMABRAin
-----------------------------
- SomaFractalMemory is the memory subsystem of SOMABRAin; it provides a stable, observable
  API that other SOMABRAin components (reasoners, planners, and agents) can call to store
  and retrieve contextual memories.

Appendix: example configuration
-------------------------------
```yaml
memory_enterprise:
  max_memory_size: 100000
  pruning_interval_seconds: 600
  decay:
    age_weight: 1.0
    recency_weight: 1.0
    access_weight: 0.5
    importance_weight: 2.0
```
