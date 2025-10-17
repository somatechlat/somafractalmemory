---
title: "Testing Guidelines"
purpose: "## Test Pyramid"
audience:
  - "Developers and Contributors"
last_updated: "2025-10-16"
---

# Testing Guidelines

## Test Pyramid

| Layer | Tools | Purpose |
|-------|-------|---------|
| Unit | `pytest`, `pytest-mock` | Validate core logic in `core.py` without hitting external services. |
| Integration | `pytest` + dockerised Postgres/Qdrant | Exercise `POST /memories`, `GET /memories/{coord}`, and search pipelines end-to-end. |
| Contract | `schemathesis` | Ensure the public OpenAPI schema matches generated responses. |

## Required Checks

- `pytest` (runs unit and integration tests)
- `ruff check .`
- `mypy somafractalmemory`

## On Pull Requests

1. Run `make lint test` before opening the PR.
2. Include new fixtures when adding fields to `/memories` payloads.
3. Update documentation within this repo if behaviour changes (especially API reference or runbooks).
4. Provide search smoke tests to confirm filters behave as expected and return JSON arrays only.

## Smoke Test Script

```bash
scripts/smoke.sh
```

The script stores, searches, fetches, and deletes a memory using the HTTP API and fails if any step returns a non-2xx status.
