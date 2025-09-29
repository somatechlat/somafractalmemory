# Architecture Overview

This document provides a high-level view of **SomaFractalMemory** (SFM): the core components, how they interact, and where each concern lives in the codebase. Every component described below is backed by real implementations—no mocks or placeholders are used outside of the explicit test mode.

---

## Component Diagram (conceptual)
```
Client (CLI / FastAPI) ──▶ Factory (`somafractalmemory.factory.create_memory_system`)
                             │
                             ▼
                    `SomaFractalMemoryEnterprise` (core orchestrator)
                  ┌──────────────┬────────────┬───────────────┐
        │              │            │               │
        ▼              ▼            ▼               ▼
     Key-Value Store   Vector Store   Graph Store   Event Producer
       (Postgres + Redis)   (Qdrant | Fast)  (NetworkX)   (Kafka/Redpanda)
```

---

## Data Flow Narrative
1. **Entry points** – Applications call the factory from the CLI (`somafractalmemory/cli.py`) or the FastAPI service (`examples/api.py`). Both paths resolve to `create_memory_system(mode, namespace, config)`.
2. **Factory wiring** – The factory inspects the requested `MemoryMode`:
   * `DEVELOPMENT` – optional Redis cache, optional Postgres backing store, Qdrant or in-memory vectors, eventing enabled by default.
   * `TEST` – fully in-memory backends (`fakeredis` and `InMemoryVectorStore`), eventing forced off.
   * `EVENTED_ENTERPRISE` / `CLOUD_MANAGED` – Postgres + Redis hybrid KV store, Qdrant vector store, eventing enabled.
3. **Core orchestration** – `SomaFractalMemoryEnterprise` owns the public API (`store_memory`, `recall`, graph helpers, decay, bulk import/export). It:
   * Serialises payloads to the KV store (JSON-first) and writes metadata for pruning.
   * Embeds payloads using a HuggingFace transformer (falls back to hash-based vectors). Embeddings are L2-normalized.
   * Upserts vectors into Qdrant (or an in-memory store in test mode). When the `SFM_FAST_CORE` flag is enabled, a parallel flat in-process slab (contiguous float32 arrays) is appended for O(n) scan with efficient NumPy dot products, bypassing the external vector store during recall.
   * Keeps an in-memory graph via `NetworkXGraphStore` for semantic links.
   * Optionally publishes events through `eventing/producer.py` when `eventing_enabled` is true.
4. **Background work** – A decay thread prunes fields based on configured thresholds; WAL reconciliation keeps vector upserts consistent if Qdrant fails temporarily.
5. **Event consumers** – `scripts/run_consumers.py` subscribes to `memory.events`, upserts canonical records via `workers/kv_writer.py`, and indexes vectors via `workers/vector_indexer.py`. Both phases emit Prometheus metrics. The fast core slab is a purely in-process acceleration layer; events remain source-of-truth for durable indexing.
6. **Observability** – API and consumers expose Prometheus metrics; OpenTelemetry instrumentation hooks psycopg2 and Qdrant at import time; Langfuse telemetry is optional and becomes a no-op when the package is missing.

---

## Key Modules
| Concern | Location | Notes |
|---------|----------|-------|
| Core API | `somafractalmemory/core.py` | `SomaFractalMemoryEnterprise` implements storage, recall, decay, graph helpers, and bulk utilities. |
| Factory | `somafractalmemory/factory.py` | Binds concrete backends based on `MemoryMode` and exposes the `PostgresRedisHybridStore`. |
| Storage Interfaces | `somafractalmemory/interfaces/storage.py` | Contracts for key-value and vector stores used across implementations. |
| Graph Interface | `somafractalmemory/interfaces/graph.py` | Contract for graph backends; default is NetworkX. |
| Storage Implementations | `somafractalmemory/implementations/storage.py` | Redis/Postgres/Qdrant clients, plus an in-memory vector store for tests. |
| Eventing | `eventing/producer.py`, `workers/*` | Schema-validated event builder, Kafka producer, and consumer workers. |
| API Example | `examples/api.py` | FastAPI surface used for local testing and documentation builds. |
| CLI | `somafractalmemory/cli.py` | Command-line interface wrapping the same factory as the API. |

---

## Production Guarantees
* **Real clients** – PostgreSQL (`psycopg2`), Redis, Qdrant, and Kafka are first-class dependencies. Test mode swaps in `fakeredis` and the in-memory vector store without altering code paths.
* **JSON-first persistence** – All payloads are serialised as JSON; legacy pickle-based storage has been removed.
* **Event schema enforcement** – Every produced message is validated against `schemas/memory.event.json`.
* **TLS/SASL hooks** – Environment variables (`POSTGRES_SSL_*`, `QDRANT_TLS`, `KAFKA_SECURITY_PROTOCOL`, etc.) are plumbed through to the respective clients.
* **Graceful degradation** – Vector failures fall back to WAL entries for later reconciliation; OpenTelemetry and Langfuse integrations quietly disable themselves when dependencies are absent.
* **Deterministic math path** – Vector embeddings are normalized; recall scoring is strictly `max(0, cosine) * importance_norm`, where `importance_norm ∈ [0,1]` is produced by an adaptive decision tree (min-max → winsor → logistic) based on the observed importance distribution (512-sample rolling reservoir). This keeps retrieval branch-free and bounded.

---

## Extensibility Points
* Implement `IVectorStore` to support an alternative ANN store (e.g., Milvus, Weaviate) and register it in the factory.
* Swap the KV layer by implementing `IKeyValueStore`; the hybrid Postgres+Redis example shows how to compose caches.
* Replace the graph backend by implementing `IGraphStore`—the default uses NetworkX, but remote graph databases can slot in.
* Extend the Kafka pipeline by adding new consumer scripts or updating `workers/vector_indexer.py`.

---

*For API surface details and configuration specifics, consult `docs/api.md` and `docs/CONFIGURATION.md`.*
