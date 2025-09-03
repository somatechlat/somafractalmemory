# SomaFractalMemory

A practical “second brain” for AI agents—store what matters, find it fast, and connect the dots.

## Overview

SomaFractalMemory is a modular memory engine for AI agents and knowledge-heavy apps. It blends fast vector similarity with a semantic graph so you can recall facts quickly and traverse relationships between them. Start lightweight with an in‑memory setup for prototyping, then flip a config to use persistent backends (like Qdrant) without changing your code. It’s configurable, observable, and test‑friendly: use the CLI or HTTP API, enable metrics and tracing when needed, and keep heavy integrations optional. “Fractal” refers to the hierarchical indexing + exact re‑rank approach that balances speed and recall while staying simple to operate.

### Highlights
- Hybrid recall: vector similarity + semantic graph traversal
- Modular backends: in‑memory, Qdrant, Redis (optional), NetworkX
- Local‑first defaults; flip a config for persistence
- CLI and HTTP API for quick integration
- Observability: metrics and structured logs
- Configurable pruning, decay, and write gating
- Test‑friendly: FakeRedis and in‑memory paths

### Common uses
- Long‑term memory for autonomous agents
- RAG caches and working memory
- Knowledge graph linking and traversal
- Durable task history and context recall

### Why “fractal”
- Hierarchical candidate selection with exact re‑rank for precision
- Scales from small prototypes to larger datasets via configuration
- Predictable performance without heavy operational overhead

## Key Features

- **Flexible Memory Modes**: Choose between `ON_DEMAND` (in-memory vectors for prototyping), `LOCAL_AGENT` (Qdrant-based persistence), or `ENTERPRISE` (tunable for high-performance use cases).
- **Hybrid Search**: Perform efficient memory recall with vector-based similarity searches, customizable via `top_k` and memory type filters.
- **Semantic Graph Traversal**: Link memories and navigate relationships using shortest-path algorithms.
- **Observability**: Built-in Prometheus metrics and Langfuse integration for monitoring and tracing.
- **CLI and HTTP API**: Intuitive command-line interface and a FastAPI-based HTTP service for easy integration.
- **Configurability**: Fine-tune memory pruning, decay thresholds, and vector dimensions via Dynaconf or environment variables.
- **Audit Logging**: Structured JSONL logs for tracking store, recall, and delete operations.

## Installation

**Note on Python Version:** This project is tested and maintained on Python 3.10 and 3.11. Some dependencies, particularly `faiss-cpu`, may not have pre-compiled wheels available for newer Python versions (like 3.12+). It is recommended to use a compatible Python version for a smooth installation.

Install the package via pip:

```bash
pip install somafractalmemory
```

For development, clone the repository and install in editable mode:

```bash
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory
pip install -e .
```

## Quickstart

Get started with a simple in-memory setup using FakeRedis for testing:

```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

# Configure a lightweight memory system
config = {
    "redis": {"testing": True},  # Use FakeRedis for testing
    "vector": {
        "backend": "faiss_aperture",
        "profile": "fast" # Choose from "fast", "balanced", or "high_recall"
    },
    "memory_enterprise": {
        "vector_dim": 768,  # Vector dimension for embeddings
        "decay": {
            "enabled": True
        }
    },
}

# Initialize an ON_DEMAND memory system
mem = create_memory_system(MemoryMode.ON_DEMAND, namespace="demo_ns", config=config)

# Store an episodic memory
coord = (1.0, 2.0, 3.0)
mem.store_memory(coord, {"task": "write documentation", "importance": 2}, memory_type=MemoryType.EPISODIC)

# Recall memories using a query
matches = mem.recall("write documentation", top_k=3)
print(matches[0])  # View the top match

# Link memories and find relationships
coord2 = (4.0, 5.0, 6.0)
mem.store_memory(coord2, {"fact": "docs published"}, memory_type=MemoryType.SEMANTIC)
mem.link_memories(coord, coord2, link_type="related")
path = mem.find_shortest_path(coord, coord2)
print(f"Shortest path: {path}")

# Note: For large memory systems, the in-memory graph should be synced explicitly
# after initialization or after large-scale imports.
# mem.sync_graph_from_memories()
```

## Command-Line Interface (CLI)

The library includes a powerful CLI for managing memories:

```bash
# Install in editable mode for CLI access
pip install -e .

# View CLI help
soma -h

# Store a memory
soma --mode local_agent --namespace demo_ns store --coord 1,2,3 --payload '{"task":"write docs","importance":2}' --type episodic

# Recall memories
soma --mode local_agent --namespace demo_ns recall --query "write documentation" --top-k 3

# Link memories
soma --mode local_agent --namespace demo_ns link --from 1,2,3 --to 4,5,6 --type related

# View system stats
soma --mode local_agent --namespace demo_ns stats
```

## Vector Backend Configuration

Switch between in-memory and Qdrant-based vector storage:

- **In-Memory (Default for ON_DEMAND)**: Ideal for prototyping.

```python
mem = create_memory_system(MemoryMode.ON_DEMAND, "demo_ns", config={"redis": {"testing": True}})
```

- **Qdrant (Default for LOCAL_AGENT/ENTERPRISE)**: Persistent storage.

```python
mem = create_memory_system(MemoryMode.ON_DEMAND, "demo_ns", config={
    "redis": {"testing": True},
    "vector": {"backend": "qdrant"}
})
```

### Optional: Fractal In-Memory backend (NumPy-only)

Hierarchical NumPy-only ANN with exact rerank, designed for strong recall without heavy deps.

Enable it in two ways:

- Set env `SFM_FRACTAL_BACKEND=1` when using `backend: "inmemory"`, or
- Select the dedicated `backend: "fractal"` and configure options explicitly.

Examples:

```python
# A) Feature-flag the fractal path while keeping backend=inmemory
config = {
    "redis": {"testing": True},
    "vector": {
        "backend": "inmemory",
        "fractal_enabled": True,               # or env SFM_FRACTAL_BACKEND=1
        "fractal": {
            "centroids": 64,                    # auto if omitted (~sqrt(N))
            "beam_width": 4,                    # explore top centroids
            "max_candidates": 1024,             # cap before exact rerank
            "rebuild_enabled": True,            # periodic/background rebuilds
            "rebuild_size_delta": 0.1,          # rebuild when size grows 10%
            "rebuild_interval_seconds": 600     # or every 10 minutes
        }
    }
}

# B) Use the dedicated fractal backend
config = {
    "redis": {"testing": True},
    "vector": {
        "backend": "fractal",
        "fractal": {"centroids": 64, "beam_width": 4}
    }
}
```

Notes:
- Exact rerank uses cosine across a capped candidate set; centroids/lists rebuild automatically.
- When disabled, it falls back to the simple in-memory store.

### Novelty-based write gate (optional)

Reduce write amplification by skipping highly redundant writes (off by default).

Enable and tune via `memory_enterprise.salience`:

```python
config = {
    "memory_enterprise": {
        "salience": {
            "novelty_gate": True,         # enable write gate
            "novelty_threshold": 0.4      # 0..1; higher means stricter gating
            # optional weights used internally (defaults are sensible)
            # "weights": {"novelty": 1.0, "error": 0.0}
        }
    }
}
```

How it works (high level):
- Computes a quick top-1 similarity against existing items; novelty = 1 - similarity.
- Combines novelty with an error term (if available) and compares against the threshold.
- If below threshold, the write is skipped; otherwise it proceeds.

## Try it: quick benchmark

You can run a small performance benchmark to sanity-check throughput and latency locally.

- Fractal backend (NumPy-only): run the benchmark at small scale to keep it fast.

```bash
python run_performance_benchmark.py --scale small --backend fractal --profile balanced
```

Notes:
- The script attempts optional baselines (Redis, FAISS). If Redis isn’t running, it will print an error for that baseline but continue.
- Metrics use psutil when available; otherwise, the script falls back to limited metrics.

## Observability

### Prometheus Metrics

Monitor store and recall operations with Prometheus:

```python
from prometheus_client import start_http
