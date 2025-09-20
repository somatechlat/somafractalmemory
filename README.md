# SomaFractalMemory

A powerful and flexible Python library for managing advanced fractal memory systems, designed to handle complex memory storage, retrieval, and linking with support for both in-memory and persistent vector backends.

## Overview

SomaFractalMemory is a cutting-edge Python package that provides a robust framework for building and interacting with fractal memory algorithms. It supports episodic and semantic memory types, hybrid search capabilities, and semantic graph traversal, making it ideal for applications requiring sophisticated memory management, such as AI agents, knowledge graphs, and data-intensive systems. The library integrates seamlessly with Redis for caching, Qdrant for vector storage, and Prometheus for observability, offering both in-memory and persistent storage options.

## Key Features

- **Flexible Memory Modes**: Choose between `ON_DEMAND` (in-memory vectors for prototyping), `LOCAL_AGENT` (Qdrant-based persistence), or `ENTERPRISE` (tunable for high-performance use cases).
- **Hybrid Search**: Perform efficient memory recall with vector-based similarity searches, customizable via `top_k` and memory type filters.
- **Semantic Graph Traversal**: Link memories and navigate relationships using shortest-path algorithms.
- **Observability**: Built-in Prometheus metrics and Langfuse integration for monitoring and tracing.
- **CLI and HTTP API**: Intuitive command-line interface and a FastAPI-based HTTP service for easy integration.
- **Configurability**: Fine-tune memory pruning, decay thresholds, and vector dimensions via Dynaconf or environment variables.
- **Audit Logging**: Structured JSONL logs for tracking store, recall, and delete operations.

## Installation

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
    "qdrant": {"path": "./qdrant.db"},  # Local Qdrant storage
    "memory_enterprise": {
        "vector_dim": 768,  # Vector dimension for embeddings
        "pruning_interval_seconds": 60,  # Prune stale memories
        "decay_thresholds_seconds": [30, 300],  # Memory decay intervals
        "decayable_keys_by_level": [["scratch"], ["low_importance"]],  # Decay rules
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
# SomaFractalMemory

SomaFractalMemory is a focused Python library that implements a hybrid, decaying memory
engine used to store, recall, and manage long-lived memories for agents and applications.
It is a core building block designed to be integrated into the broader SOMABRAin family of
components — SOMABRAin is the name used for the platform that orchestrates agent memory,
reasoning, and tooling; SomaFractalMemory provides the memory substrate.

This `README` is written for humans who want to understand what the project does, how to
run it locally, and how it fits into SOMABRAin.

Why this project exists
-----------------------
Agents and long-running systems need a memory that is:

- semantically searchable (vector embeddings),
- cheap and reliable to read/write (key-value storage),
- able to explicitly link related memories (graph), and
- capable of aging and pruning memories automatically (eviction/decay).

SomaFractalMemory implements those pieces, with conservative defaults and explicit opt-ins
for any behavior that could be surprising (network downloads, arbitrary deserialization).

Quick summary — what it provides
--------------------------------

- Pluggable KV, vector, and graph stores (in-memory, Redis, Qdrant, NetworkX graph, etc.).
- JSON-first serialization with an opt-in Pickle fallback for trusted environments.
- Embedding provider that uses a HF Transformer when explicitly enabled, otherwise a
    deterministic hash-based fallback.
- Eviction scoring that combines age, recency, access count, and importance into a single
    score used to keep the working set bounded.
- Low-cardinality Prometheus metrics to observe store/recall latency, WAL backlog, and
    eviction activity.

Install (development)
---------------------

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests
---------

```bash
source .venv/bin/activate
pytest tests/
```

Basic usage example
-------------------

```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

mem = create_memory_system(MemoryMode.ON_DEMAND, "demo")
coord = (1.0, 2.0)
mem.store_memory(coord, {"task": "remember this", "importance": 1})
results = mem.recall("remember this", top_k=5)
print(results)
```

Important environment variables and opt-ins
-----------------------------------------

- `SOMA_ALLOW_PICKLE` (default: "false"): if set to "true", allows pickle serialization
    as a fallback when JSON fails. This must only be enabled in trusted environments.
- `SOMA_ALLOW_UNPINNED_HF` (default: "false"): if true, allows unpinned HuggingFace
    model downloads. By default, transformer models are only used if explicitly pinned with
    `SOMA_MODEL_REV`.
- `SOMA_MODEL_REV` (optional): pin HF model revision when loading.
- `SOMA_MAX_MEMORY_SIZE` (default from factory or env): maximum number of memories before
    eviction is triggered.
- `SOMA_NAMESPACE`: default namespace key prefix used by the instance.

Eviction math (human explanation)
--------------------------------

Each memory gets an eviction score computed as a linear combination of age and recency
penalties, reduced by access_count and importance bonuses. The higher the score, the more
eligible the memory is for pruning. Informally:

score = (age_weight * age_hours)
            + (recency_weight * recency_hours)
            - (access_weight * access_count)
            - (importance_weight * importance)

This formula is intentionally simple and tunable via environment variables:
`SOMA_DECAY_AGE_WEIGHT`, `SOMA_DECAY_RECENCY_WEIGHT`, `SOMA_DECAY_ACCESS_WEIGHT`, and
`SOMA_DECAY_IMPORTANCE_WEIGHT`.

Observability — Prometheus metrics
---------------------------------

Metrics are registered to the default Prometheus registry so a process that calls
`prometheus_client.start_http_server(port)` exposes them at `/metrics`.

Main metrics (low-cardinality):

- `soma_memory_store_total{namespace}` — counter for store operations
- `soma_memory_recall_total{namespace}` — counter for recall operations
- `soma_memory_store_latency_seconds{namespace}` — histogram of store latencies
- `soma_memory_recall_latency_seconds{namespace}` — histogram of recall latencies
- `soma_vector_upsert_total{namespace}` — counter for vector upserts
- `soma_eviction_pruned_total` — counter for how many memories were pruned
- `soma_eviction_index_size{namespace}` — gauge for eviction index size
- `soma_wal_entries_pending{namespace}` — gauge for pending WAL backlog

Design choices and trade-offs
---------------------------

- Safety-first defaults: pickled data and unpinned model downloads are opt-in to avoid
    surprising behavior in secure or offline environments.
- Low-cardinality labels (namespace only) keep Prometheus usage cheap and scalable; avoid
    adding per-memory or high-cardinality labels.
- Metrics are created once (module-level) and bound to a `namespace` label per instance so
    multiple instances/processes don't collide when registered.

How this fits into SOMABRAin
----------------------------

SOMABRAin is the larger platform that orchestrates agents, memory, and reasoning pipelines.
Within SOMABRAin, SomaFractalMemory plays the role of the memory substrate — a component
that stores, ages, and serves memories for agents. Other SOMABRAin components may:

- call the `recall` APIs to retrieve relevant memories for a given agent context,
- enrich memories with model-inferred predictions (prediction providers that integrate with
    external systems), and
- visualize or alert on metrics and health checks collected from `soma` instances.

Contributing and safety
-----------------------

Follow the repository `CONTRIBUTING.md` and `SECURITY.md` for contribution guidelines and
responsible disclosure. When adding new features, prefer opt-ins for behavior that could
introduce network activity or execute untrusted code.

Further reading and docs
------------------------

This README is a user-facing summary. A canonical, more technical specification lives in
`docs/README_canonical.md` (added alongside this file) and contains architecture diagrams,
serialization details, the exact eviction formula, and operational notes.

License
-------

See the `LICENSE` file in this repository.
