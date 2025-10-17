---
title: "Domain Knowledge"
purpose: "- **Memory Types**: `episodic` memories represent time-bound events; `semantic` memories represent durable facts."
audience:
  - "New Team Members"
last_updated: "2025-10-16"
---

# Domain Knowledge

- **Memory Types**: `episodic` memories represent time-bound events; `semantic` memories represent durable facts. The API defaults to `episodic` but both share the same storage pipeline.
- **Coordinates**: Treated as deterministic identifiers. Clients should store the coordinate string they send to `/memories` for future retrieval/deletion.
- **Hybrid Search**: Combines vector similarity with metadata filters. Turned on by default; disable via `SOMA_HYBRID_RECALL_DEFAULT=0` if necessary for experiments.
- **Rate Limiting**: Global limiter protects all routes; tune via `SOMA_RATE_LIMIT_MAX` and `SOMA_RATE_LIMIT_WINDOW_SECONDS`.
- **Deprecations**: Graph operations, bulk store endpoints, and bespoke recall variants were removed. Do not reintroduce them.
