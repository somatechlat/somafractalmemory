---
title: "API Design Analysis"
purpose: "Evaluate the SomaFractalMemory HTTP surface against the product mandate"
audience:
  - "Architecture Team"
  - "Product Leads"
  - "API Designers"
version: "2.1.0"
date: "2025-10-16"
---

# API Design Analysis: Core Purpose Alignment

## TL;DR

**Alignment score: 4.6 / 5.** The service now centres on a single `/memories` contract that excels at the project mission: store, search, fetch, and delete agent memories. Operational probes are intentionally separated and unauthenticated.

## Current Surface

| Category | Endpoint | Notes |
|----------|----------|-------|
| Store | `POST /memories` | Idempotent via coordinate overwrite. |
| Retrieve | `GET /memories/{coord}` | Returns canonical payload + metadata. |
| Delete | `DELETE /memories/{coord}` | Removes payload and vector entry. |
| Search | `POST /memories/search` / `GET /memories/search` | Hybrid vector + metadata filters. |
| Operations | `/stats`, `/health`, `/healthz`, `/readyz`, `/metrics`, `/ping`, `/` | Public, rate limited. |

No other HTTP endpoints are supported. CLI and documentation reflect the same set.

## Design Principles

1. **Single mental model**: All workflows are variants of CRUD on memories.
2. **Predictable payloads**: Request/response models rely on Pydantic schemas (`MemoryStoreResponse`, `MemorySearchResponse`, etc.).
3. **Operational clarity**: Probes live under their own tags and require no authentication.
4. **Extensibility via parameters**: Metadata filters and optional `memory_type` allow evolution without exploding endpoint count.

## Risks & Mitigations

| Risk | Status | Mitigation |
|------|--------|------------|
| Graph utilities still exist in `core.py`. | Medium | Track removal / segregation in a future major release. They are not reachable via HTTP or CLI. |
| SDKs outside repo may still target `/store`. | Medium | Communicate breaking change and publish migration notes referencing the new docs. |
| Documentation drift | Low | Template enforcement (single approved tree) plus audits reduces risk. |

## Recommendations

1. **Boundary enforcement**: Add automated tests to confirm `/store`, `/recall`, `/link`, etc. return 404.
2. **Progressive cleanup**: Isolate graph-related helpers behind feature flags or remove entirely once unused.
3. **Usage telemetry**: Track `/memories/search` filter usage to inform future schema extensions.

## Manifesto (v2)

```
✅ Exactly one way to store memories: POST /memories
✅ Exactly one way to retrieve a specific memory: GET /memories/{coord}
✅ Exactly one hybrid search surface: /memories/search (POST/GET)
✅ Only public probes outside the memory namespace
✅ Documentation and tooling reference only the routes above
```

The API currently satisfies the manifesto. Any proposal for additional routes must justify why parameters or payload evolution are insufficient.
