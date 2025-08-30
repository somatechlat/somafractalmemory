# SomaFractalMemoryEnterprise: Modules, Features, and Project Overview

## Modules

- `somafractalmemory/core.py`: Main logic for memory storage, retrieval, embedding, and semantic graph.
- `somafractalmemory/__init__.py`: Package initializer.
- `tests/`: Unit and integration tests for core, enterprise, and semantic graph features.
- `ARCHITECTURE.md`: Architecture, roadmap, and improvement plan.
- `README.md`: Basic usage and installation instructions.
- `docs.md`: Feature summary and getting started.
- `CONTRIBUTING.md`: Contribution guidelines.

## Features

- **Memory Storage/Recall**: Episodic and semantic memory, vector search, hybrid search.
- **Semantic Graph**: Node/edge management, export/import, shortest path, neighbor queries.
- **Multi-modal Embedding**: Text, image, and audio embedding (stubbed, extendable).
- **Predictive Memory**: (Configurable) LLM-based prediction and confidence for each memory.
- **Distributed Support**: Redis, Qdrant, FAISS, optional Kafka/NATS for event streaming.
- **Observability**: Logging, Prometheus metrics, planned dashboard.
- **Agent-Centric Features**: Self-reflection, memory prioritization, meta-memory (planned).
- **Cost-Saving**: Caching, batching, importance filtering (planned).
- **Multi-Agent Support**: Namespaces, agent IDs (planned).
- **Policy/Safety Layer**: Configurable rules for LLM and memory usage (planned).

## Project Structure

- `somafractalmemory/` (core logic)
- `tests/` (unit/integration tests)
- `qdrant.db/` (local vector DB)
- `requirements.txt`, `pyproject.toml` (dependencies)
- `ARCHITECTURE.md`, `README.md`, `docs.md`, `CONTRIBUTING.md`

## How to Use for Context Recovery

- **Architecture & Roadmap**: See `ARCHITECTURE.md` for high-level design, features, and priorities.
- **Modules & Features**: This file (`PROJECT_OVERVIEW.md`) for quick reference to all modules and features.
- **API & Usage**: See `README.md` and `core.py` for main classes and methods.
- **Tests**: See `tests/` for usage patterns and expected behaviors.
- **Contribution & Docs**: See `CONTRIBUTING.md` and `docs.md`.

*Update this file as modules/features evolve. Use it to quickly regain project context if chat history is lost.*
