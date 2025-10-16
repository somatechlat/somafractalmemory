# API Reference

This document provides a detailed reference for the `SomaFractalMemoryEnterprise` class, which is the central component of the Soma Fractal Memory system.

## `SomaFractalMemoryEnterprise`

The `SomaFractalMemoryEnterprise` class provides a unified interface for all memory operations, including storing, recalling, and linking memories.

### Initialization

```python
def __init__(
    self,
    namespace: str,
    kv_store: IKeyValueStore,
    vector_store: IVectorStore,
    graph_store: IGraphStore,
    model_name: str = "microsoft/codebert-base",
    vector_dim: int = 768,
    encryption_key: Optional[bytes] = None,
    config_file: str = "config.yaml",
    max_memory_size: int = 100000,
    pruning_interval_seconds: int = 600,
    decay_thresholds_seconds: Optional[List[int]] = None,
    decayable_keys_by_level: Optional[List[List[str]]] = None,
    decay_enabled: bool = True,
    reconcile_enabled: bool = True,
) -> None:
```

**Parameters:**

*   `namespace` (str): The namespace for all memory operations.
*   `kv_store` (IKeyValueStore): The key-value store backend.
*   `vector_store` (IVectorStore): The vector store backend for embeddings and similarity search.
*   `graph_store` (IGraphStore): The graph store backend for semantic links.
*   `model_name` (str): The name of the transformer model to use for embeddings.
*   `vector_dim` (int): The dimension of the vectors.
*   `encryption_key` (Optional[bytes]): The encryption key for encrypting memory payloads.
*   `config_file` (str): The path to the configuration file.
*   `max_memory_size` (int): The maximum number of memories to store.
*   `pruning_interval_seconds` (int): The interval in seconds for pruning old memories.
*   `decay_thresholds_seconds` (Optional[List[int]]): The decay thresholds in seconds.
*   `decayable_keys_by_level` (Optional[List[List[str]]]): The keys to decay at each level.
*   `decay_enabled` (bool): Whether to enable memory decay.
*   `reconcile_enabled` (bool): Whether to enable reconciliation of the write-ahead log.

### Methods

| Method | Description |
|--------|-------------|
| `store_memory(coord, payload, memory_type=MemoryType.EPISODIC)` | High-level store that writes to the KV store, upserts into Qdrant, updates metadata, and optionally emits a Kafka event. |
| `remember(payload, coordinate=None, memory_type=MemoryType.EPISODIC)` | Convenience wrapper that auto-generates coordinates. |
| `recall(query, top_k=5, memory_type=None)` | Hybrid recall against the vector store, falling back to KV when necessary. |
| `recall_with_scores(query, top_k=5, memory_type=None)` | Adds similarity scores to recall results. |
| `find_hybrid_with_context(query, context, top_k=5, memory_type=None)` | Recall augmented with caller-provided context filters. |
| `find_by_coordinate_range(min_coord, max_coord, memory_type=None)` | Range query over stored coordinates. |
| `link_memories(from_coord, to_coord, link_type="related", weight=1.0)` | Create/update an edge in the graph store. |
| `find_shortest_path(from_coord, to_coord, link_type=None)` | Graph traversal. |
| `get_linked_memories(coord, link_type=None, depth=1)` | Retrieves memories linked to a given memory. |
| `delete(coordinate)` / `delete_many(coordinates)` | Remove memories from KV, vector store, and graph. |
| `export_memories(path)` / `import_memories(path, replace=False)` | JSONL export/import helpers. |
| `memory_stats()` | Aggregate statistics and backend health checks. |
| `health_check()` | Boolean health map for KV, vector, and graph stores. |
| `run_decay_once()` / `_decay_memories()` | Apply configured decay rules (invoked on a background thread). |
| `with_lock(name, func, *args, **kwargs)` | Execute a callable under the KV-backed lock abstraction. |

---

## CLI (`somafractalmemory/cli.py`)
The `soma` entry point supports the following sub-commands:

| Command | Purpose |
|---------|---------|
| `store` | Store a single memory (`--coord`, `--payload`, `--type`). |
| `recall` | Recall memories (`--query`, `--top-k`, optional `--type`). |
| `link` | Create a graph link (`--from`, `--to`, `--type`, `--weight`). |
| `path` | Shortest path in the semantic graph (`--from`, `--to`). |
| `neighbors` | List neighbours around a coordinate. |
| `stats` | Dump `memory_stats()` as JSON. |
| `export-memories` / `import-memories` | Persist or load memories in newline-delimited JSON. |
| `delete-many` | Remove multiple coordinates in one call. |
| `store-bulk` | Load a JSON file containing `coord/payload/type` items and store them batch-wise. |
| `range` | Query coordinates within a bounding box. |

---

## FastAPI Surface (`somafractalmemory/http_api.py`)
The example application wires `MEMORY_MODE=evented_enterprise` with Redis/Postgres/Qdrant based on environment, instruments endpoints for Prometheus, and serves OpenAPI at `/openapi.json`. Key routes:

### Memory Operations
- `POST /store` – body: `{coord: str, payload: dict, type: "episodic"|"semantic"}`
- `POST /remember` – body: `{payload: dict, coord?: str, type?: str}`
- `POST /recall` – body: `{query: str, top_k?: int, type?: str, filters?: dict}`
- `POST /store_bulk`
- `POST /recall_with_scores`
- `POST /recall_with_context`
- `GET  /range`

### Graph Operations
- `POST /link`
- `GET  /neighbors`
- `GET  /shortest_path`

### System & Admin
- `GET  /stats`
- `GET  /metrics`
- `GET  /health`
- `GET  /healthz`
- `GET  /readyz`
- Root (`GET /`) returns a simple JSON banner with the metrics URL.

Each endpoint requires the configured bearer token (`SOMA_API_TOKEN`) via FastAPI dependencies and enforces rate limiting controlled by `SOMA_RATE_LIMIT_MAX`.

---

## Event Interfaces
- `eventing/producer.py` exposes `build_memory_event(namespace, payload)` and `produce_event(event, topic="memory.events")`. Both rely on `confluent_kafka` and validate events against `schemas/memory.event.json`.
- `workers/kv_writer.py` and `workers/vector_indexer.py` define `process_message`/`index_event` helpers invoked by `scripts/run_consumers.py`. Messages are dictionaries matching the schema above.

---

## Health & Metrics
- API metrics: `/metrics` (Prometheus text). Counters include `soma_memory_store_total`, `soma_memory_store_latency_seconds`, and a custom 404 counter.
- Consumer metrics: exported from `scripts/run_consumers.py` on `CONSUMER_METRICS_PORT` (default `8001`).
