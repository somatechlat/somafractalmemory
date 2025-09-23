# SOMA FRAC T AL MEMORY

[![Documentation](https://img.shields.io/badge/docs‑latest-blue.svg)](docs/index.md)

A powerful and flexible Python library for managing advanced fractal memory systems, designed to handle complex memory storage, retrieval, and linking with support for both in‑memory and persistent vector backends.

## Overview

SomaFractalMemory provides a robust framework for building and interacting with fractal memory algorithms. It supports episodic and semantic memory types, hybrid search capabilities, and semantic graph traversal, making it ideal for AI agents, knowledge graphs, and data‑intensive systems. The library integrates seamlessly with Redis for caching, Qdrant for vector storage, and Prometheus for observability, offering both in‑memory and persistent storage options.

## Quickstart

```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

# Minimal in‑memory test configuration
config = {
    "redis": {"testing": True},
    "qdrant": {"path": "./qdrant.db"},
}

mem = create_memory_system(MemoryMode.TEST, "demo_ns", config=config)
coord = (1.0, 2.0, 3.0)
mem.store_memory(coord, {"task": "write docs", "importance": 2}, MemoryType.EPISODIC)
print(mem.recall("write docs"))
```

For a full guide, see the consolidated documentation:
- **Index / Overview** – `docs/index.md`
- **Public API** – `docs/api.md`
- **Configuration reference** – `docs/configuration.md`
- **Architecture diagram** – `docs/architecture.md`

## Command‑Line Interface (CLI)

```bash
# Install in editable mode for CLI access
pip install -e .

# Show help
soma -h
```

The CLI mirrors the Python API and supports store, recall, linking, and stats commands. See `docs/README.md` for detailed usage.

## Observability & Event Publishing

- **Prometheus metrics** are exposed via the built‑in counters and histograms.
- **OpenTelemetry** automatically traces PostgreSQL and Qdrant calls.
- **Kafka events** are emitted after each successful `store_memory` when `eventing.enabled` is true (see `docs/CONFIGURATION.md`).

## Docker Compose Setup

The project can be run locally using Docker Compose. All services (Redis, Qdrant, PostgreSQL, Redpanda, FastAPI API, and the consumer) are defined in `docker-compose.yml` and use **named volumes** for persistent storage.

### 1. Prepare the environment file
Create a copy of the example and adjust values if needed:
```bash
cp .env.example .env   # edit .env as required (e.g., MEMORY_MODE)
```
The `.env` file is automatically loaded by Docker Compose because the compose file now contains `env_file: .env`.

### 2. Build the images
```bash
docker compose build
```
If the build succeeds you will see each service being built, e.g., `api` and `consumer` from the repository's `Dockerfile`.

### 3. Start the stack
```bash
docker compose up -d
```
All services will start in the background. The FastAPI server is exposed on **http://localhost:9595**.

### 4. Dynamic configuration
* **CLI helper** – Run the provided script to change configuration from the terminal:
```bash
./configure.sh MEMORY_MODE=evented_enterprise
```
The script updates `.env` and runs `docker compose up -d --build api` to apply the change without affecting other services.

### 5. Stop the stack
```bash
docker compose down
```
The named volumes (`redis_data`, `qdrant_storage`, `postgres_data`, `redpanda_data`) keep their data, so you can restart later without data loss.

---

For more detailed architecture information see the up‑to‑date documentation in `docs/ARCHITECTURE.md`.
