# somafractalmemory

A world-class Python package for advanced fractal memory algorithms.

## Installation

```bash
pip install somafractalmemory
```

## Quickstart

```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

# Minimal local setup using FakeRedis and on-disk Qdrant
config = {
    "redis": {"testing": True},
    "qdrant": {"path": "./qdrant.db"},
    # Optional: memory tuning
    "memory_enterprise": {
        "vector_dim": 768,
        "pruning_interval_seconds": 60,
        "decay_thresholds_seconds": [30, 300],
        "decayable_keys_by_level": [["scratch"], ["low_importance"]],
    },
}

# Use in-memory vectors for ON_DEMAND (default), or Qdrant with LOCAL_AGENT
mem = create_memory_system(MemoryMode.ON_DEMAND, "demo_ns", config={"redis": {"testing": True}})

# Store an episodic memory
coord = (1.0, 2.0, 3.0)
mem.store_memory(coord, {"task": "write docs", "importance": 2}, memory_type=MemoryType.EPISODIC)

# Recall using hybrid search
matches = mem.recall("write documentation", top_k=3)
print(matches[0])

# Link memories and traverse the semantic graph
coord2 = (4.0, 5.0, 6.0)
mem.store_memory(coord2, {"fact": "docs published"}, memory_type=MemoryType.SEMANTIC)
mem.link_memories(coord, coord2, link_type="related")
path = mem.find_shortest_path(coord, coord2)
print(path)
```

## CLI

Install the package in editable mode and use the built-in CLI:

```bash
# from repo root
pip install -e .

# Show help
soma -h

# Store a memory (episodic)
soma --mode local_agent --namespace demo_ns store --coord 1,2,3 --payload '{"task":"write docs","importance":2}' --type episodic

# Recall
soma --mode local_agent --namespace demo_ns recall --query "write documentation" --top-k 3

# Link memories
soma --mode local_agent --namespace demo_ns link --from 1,2,3 --to 4,5,6 --type related

# Stats
soma --mode local_agent --namespace demo_ns stats

### Vector backend toggle

- ON_DEMAND now defaults to an in-memory vector store for fast prototyping. To force Qdrant:

```python
create_memory_system(MemoryMode.ON_DEMAND, "demo_ns", config={
  "redis": {"testing": True},
  "vector": {"backend": "qdrant"}
})
```

- LOCAL_AGENT/ENTERPRISE default to Qdrant; to use in-memory vectors, set `config={"vector": {"backend": "inmemory"}}`.
```

## Observability

- Prometheus: The core records counters and histograms for store operations (`soma_memory_store_total`, `soma_memory_store_latency_seconds`). To expose metrics:

```python
from prometheus_client import start_http_server
start_http_server(8000)  # then scrape http://localhost:8000/
```

- Langfuse: Configured via Dynaconf or environment:
  - `langfuse_public`, `langfuse_secret`, `langfuse_host` in `config.yaml`, or env vars `SOMA_LANGFUSE_PUBLIC`, etc.
  - Core initializes a client; integrate traces in your application as needed.

### Logging

Enable structured logs or basic logging at startup:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Audit log

- The core writes structured JSONL audit events to `audit_log.jsonl` for store/recall/forget via default hooks.
- Format: one JSON object per line, including action, timestamp, and optional extra fields.

## Configuration

- The core also reads settings from Dynaconf (`config.yaml`) and environment (prefix `SOMA_`).
- See `config.example.yaml` for a starting point; copy it to `config.yaml` and adjust.

See also: `CONFIGURATION.md` for full key and environment variable mappings.

## API Schema (OpenAPI)

- A static OpenAPI 3.0 schema is included at `openapi.json` matching the FastAPI example in `examples/api.py`.
- The example app also serves a live schema at `/openapi.json` when running.

## Development

## Development

- Create venv and install dev deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Install package editable for CLI: `pip install -e .`
- Run tests: `pytest -q`
  - If using the repo’s venv: `.venv/bin/pytest -q`
- Clean workspace (ignored artifacts):
  - `make clean` or manually remove: `.pytest_cache`, `__pycache__`, `somafractalmemory.egg-info`, `qdrant.db`, `*.index`, `*_qdrant`, `audit_log.jsonl`.
- Explore examples:
  - `examples/quickstart.py`: basic store/recall/link usage
  - `examples/metrics_server.py`: expose Prometheus metrics on port 8000
  - `examples/api.py`: FastAPI service with store/recall/stats

## HTTP API (example)

The FastAPI example (`examples/api.py`) exposes:

- POST `/store` body: `{coord: "1,2,3", payload: {...}, type: "episodic|semantic"}`
- POST `/recall` body: `{query: str, top_k?: int, type?: "episodic|semantic"}`
- POST `/recall_with_scores` body: `{query: str, top_k?: int, type?: ...}`
- POST `/recall_with_context` body: `{query: str, context: {...}, top_k?: int, type?: ...}`
- POST `/link` body: `{from_coord: "1,2,3", to_coord: "4,5,6", type?: "related"}`
- GET `/neighbors?coord=1,2,3&link_type=related`
- GET `/shortest_path?frm=1,2,3&to=4,5,6&link_type=related`
- POST `/export_memories` body: `{path: "mem.jsonl"}`
- POST `/import_memories` body: `{path: "mem.jsonl", replace?: bool}`
- POST `/delete_many` body: `{coords: ["1,2,3", "4,5,6"]}`
- POST `/store_bulk` body: `{items: [{coord, payload, type}, ...]}`
- GET `/stats`, GET `/health`

Auth and rate limiting:
- Set `SOMA_API_TOKEN` to require `Authorization: Bearer <token>` header.
- Simple per-path 60 req/minute rate limiter is enabled in the example.

Curl examples (with token):

```bash
export SOMA_API_TOKEN=mytoken
# Start API: uvicorn examples.api:app --reload

curl -X POST http://localhost:8000/store \
  -H "Authorization: Bearer $SOMA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"coord":"1,2,3","payload":{"task":"x"},"type":"episodic"}'

curl -X POST http://localhost:8000/recall \
  -H "Authorization: Bearer $SOMA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"x","top_k":1}'
```

### Docker (API example)

Build and run the FastAPI example in Docker:

```bash
docker build -t somafractal-api .
docker run --rm -p 8000:8000 -e SOMA_API_TOKEN=mytoken somafractal-api
```

### Benchmark

Run a simple benchmark for store/recall throughput and latency:

```bash
make bench
# or customize
python examples/benchmark.py --n 5000 --dim 256
```

## License

See LICENSE for details.
