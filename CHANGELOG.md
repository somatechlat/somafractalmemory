# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-09-02
### Added
- Initial public release with src/ packaging, CI, and docs skeleton.
- Consolidated contributing guide and versioning policy.
- Comprehensive .gitignore and repo hygiene.

## [0.2.0] - 2025-08-30
### Added
- Core: store/recall (context/scored/filters), decay + memory cap, versioning, hooks, coordinate-range search.
- Import/Export: JSONL export/import; bulk store and batch delete.
- Graph: link management, neighbors, weighted shortest path, GraphML export/import.
- Backends: FakeRedis + local Qdrant vector store; NetworkX graph; prediction provider stubs.
- CLI: store/recall/link/path/neighbors/range, bulk store, delete-many, export/import memories/graph.
- API (FastAPI example): endpoints for store/recall(+scores/+context/+batch), link/neighbors/shortest_path, range, bulk, export/import, delete_many, stats/health, simple token auth + rate limiting.
- Observability: Prometheus counters and histograms; metrics server example; benchmark script.
- Tooling: Dockerfile, GitHub Actions (pytest + mypy), Makefile targets, typing improvements, mypy configuration.
- Docs: README, CONFIGURATION, PERFORMANCE, MEMORY_SCHEMA; examples (quickstart, metrics_server, seed_and_query).

### Changed
- Modernized Qdrant client usage (collection_exists/create_collection; query_points with search fallback).

### Notes
- Optional encryption for sensitive fields (`task`, `code`) is enabled when `cryptography` is installed and a key is provided.
