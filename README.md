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

# Initialize a TEST memory system
mem = create_memory_system(MemoryMode.TEST, namespace="demo_ns", config=config)

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
print(path)  # Display the traversal path
```

## Command-Line Interface (CLI)

The library includes a powerful CLI for managing memories:

```bash
# Install in editable mode for CLI access
pip install -e .

# View CLI help
soma -h

# Store a memory (use v2 canonical mode)
soma --mode development --namespace demo_ns store --coord 1,2,3 --payload '{"task":"write docs","importance":2}' --type episodic

# Recall memories
soma --mode development --namespace demo_ns recall --query "write documentation" --top-k 3

# Link memories
soma --mode development --namespace demo_ns link --from 1,2,3 --to 4,5,6 --type related

# View system stats
soma --mode development --namespace demo_ns stats
```

## Vector Backend Configuration

Switch between in-memory and Qdrant-based vector storage:

- **In-Memory (Default for ON_DEMAND)**: Ideal for prototyping.

```python
mem = create_memory_system(MemoryMode.TEST, "demo_ns", config={"redis": {"testing": True}})
```

- **Qdrant (Default for LOCAL_AGENT/ENTERPRISE)**: Persistent storage.

```python
mem = create_memory_system(MemoryMode.TEST, "demo_ns", config={
    "redis": {"testing": True},
    "vector": {"backend": "qdrant"}
})
```

## Observability

### Prometheus Metrics

Monitor store and recall operations with Prometheus:

```python
from prometheus_client import start_http
