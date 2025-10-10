# Public API Reference

This reference covers the primary classes, enums, and functions exposed by the `somafractalmemory` package, plus the CLI and FastAPI surfaces that ship with the repository. All content is generated manually from the current code to ensure it stays in sync.

---

## Factory Entry Point
```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

mem = create_memory_system(
    MemoryMode.DEVELOPMENT,
    "demo",
    config={
        "redis": {"testing": True},
        "qdrant": {"path": "./qdrant.db"},
    },
)
```

### `MemoryMode`
Enum defined in `somafractalmemory/factory.py`:
- `DEVELOPMENT`
- `TEST`
- `EVENTED_ENTERPRISE`
- `CLOUD_MANAGED`

### `MemoryType`
Enum defined in `somafractalmemory/core.py`:
- `EPISODIC`
- `SEMANTIC`

### `create_memory_system(mode, namespace, config=None)`
Returns a configured `SomaFractalMemoryEnterprise` instance. Key behaviour:
- Selects Redis/Postgres/Qdrant implementations based on `mode` and `config`.
- Attaches a `NetworkXGraphStore` in all modes.
- Sets `memory.eventing_enabled` depending on configuration (forced `False` in `TEST`).

---

## `SomaFractalMemoryEnterprise`
Located in `somafractalmemory/core.py`. Notable methods:

| Method | Description |
|--------|-------------|
| `store_memory(coord, payload, memory_type=MemoryType.EPISODIC)` | High-level store that writes to the KV store, upserts into Qdrant, updates metadata, and optionally emits a Kafka event. |
| `remember(payload, coordinate=None, memory_type=MemoryType.EPISODIC)` | Convenience wrapper that auto-generates coordinates. |
| `recall(query, top_k=5, memory_type=None)` | Hybrid recall against the vector store, falling back to KV when necessary. |
| `recall_batch(queries, top_k=5, memory_type=None, filters=None)` | Multi-query recall helper. |
| `recall_with_scores(query, top_k=5, memory_type=None)` | Adds similarity scores to recall results. |
| `find_hybrid_with_context(query, context, top_k=5, memory_type=None)` | Recall augmented with caller-provided context filters. |
| `find_by_coordinate_range(min_coord, max_coord, memory_type=None)` | Range query over stored coordinates. |
| `link_memories(from_coord, to_coord, link_type="related", weight=1.0)` | Create/update an edge in the graph store. |
| `find_shortest_path(from_coord, to_coord, link_type=None)` | Graph traversal via `NetworkXGraphStore`. |
| `get_neighbors(coord, link_type=None, limit=None)` | Provided through the graph store (`GraphStore.get_neighbors`). |
| `delete(coordinate)` / `delete_many(coordinates)` | Remove memories from KV, vector store, and graph. |
| `export_memories(path)` / `import_memories(path, replace=False)` | JSONL export/import helpers. |
| `memory_stats()` | Aggregate statistics and backend health checks. |
| `health_check()` | Boolean health map for KV, vector, and graph stores. |
| `run_decay_once()` / `_decay_memories()` | Apply configured decay rules (invoked on a background thread). |
| `with_lock(name, func, *args, **kwargs)` | Execute a callable under the KV-backed lock abstraction. |

The class also exposes lower-level helpers (`store`, `iter_memories`, `embed_text`, WAL reconciliation) that are exercised by the tests and workers.

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

All commands accept `--mode`, `--namespace`, and optional `--config-json` to provide a configuration dictionary identical to the one passed to `create_memory_system`.

---

## FastAPI Surface (`somafractalmemory/http_api.py`)
The example application wires the selected `MEMORY_MODE` (default DEVELOPMENT) with Redis/Postgres/Qdrant based on environment, instruments endpoints for Prometheus, and serves OpenAPI at `/openapi.json`. Key routes:

### Memory Operations
- `POST /store` – body: `{coord: str, payload: dict, type: "episodic"|"semantic"}`
- `POST /remember` – body: `{payload: dict, coord?: str, type?: str}`
- `POST /recall` – body: `{query: str, top_k?: int, type?: str, filters?: dict}`
- `POST /recall_batch`
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

Each endpoint uses FastAPI dependencies for optional bearer-token auth (`SOMA_API_TOKEN`) and simple rate limiting controlled by `SOMA_RATE_LIMIT_MAX`.

---

## Event Interfaces
- `eventing/producer.py` exposes `build_memory_event(namespace, payload)` and `produce_event(event, topic="memory.events")`. Both rely on `confluent_kafka` and validate events against `schemas/memory.event.json`.
- `workers/kv_writer.py` and `workers/vector_indexer.py` define `process_message`/`index_event` helpers invoked by `scripts/run_consumers.py`. Messages are dictionaries matching the schema above.

---

## Health & Metrics
- API metrics: `/metrics` (Prometheus text). Counters include `soma_memory_store_total`, `soma_memory_store_latency_seconds`, and a custom 404 counter.
- Consumer metrics: exported from `scripts/run_consumers.py` on `CONSUMER_METRICS_PORT` (default `8001`).

---

*For configuration details consult `docs/CONFIGURATION.md`. For operational runbooks see `docs/CANONICAL_DOCUMENTATION.md`.*
