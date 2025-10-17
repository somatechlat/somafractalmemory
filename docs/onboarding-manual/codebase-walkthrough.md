---
title: "Codebase Walkthrough"
purpose: "| Path | Description | |------|-------------| | `somafractalmemory/http_api.py` | FastAPI application exposing `/memories` endpoints plus operational probes."
audience:
  - "New Team Members"
last_updated: "2025-10-16"
---

# Codebase Walkthrough

| Path | Description |
|------|-------------|
| `somafractalmemory/http_api.py` | FastAPI application exposing `/memories` endpoints plus operational probes. |
| `somafractalmemory/core.py` | Core memory engine (storage, embeddings, hybrid search). Graph helpers remain internal only and are slated for future removal. |
| `somafractalmemory/cli.py` | CLI that mirrors the API (store, search, get, delete, stats). |
| `somafractalmemory/factory.py` | Factory for instantiating the memory system across environments. |
| `tests/` | PyTest suite covering core logic and API behaviours. |
| `docs/` | Documentation following the four-manual template. |

Start by reading `http_api.py` and the Development Manual's API reference to understand the request/response models.
