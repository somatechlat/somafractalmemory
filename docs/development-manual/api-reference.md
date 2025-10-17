---
title: "API Reference (v2)"
purpose: "All endpoints require the `Authorization: Bearer <token>` header unless noted."
audience:
  - "Developers and Contributors"
last_updated: "2025-10-16"
---

# API Reference (v2)

All endpoints require the `Authorization: Bearer <token>` header unless noted. The base URL is `https://<host>`.

## `POST /memories`

Store or overwrite a memory at a coordinate.

**Request Body**
```json
{
  "coord": "string",          // comma-separated floats
  "payload": { "any": "json" },
  "memory_type": "episodic" | "semantic" (optional, default "episodic")
}
```

**Response**
```json
{
  "coord": "string",
  "memory_type": "episodic",
  "ok": true
}
```

## `GET /memories/{coord}`

Retrieve the memory stored at `coord`.

**Response**
```json
{
  "memory": {
    "coordinate": [float, ...],
    "payload": {}
  }
}
```

- Returns `404` if no memory exists.

## `DELETE /memories/{coord}`

Delete the memory at `coord`.

**Response**
```json
{ "coord": "string", "deleted": true }
```

## `POST /memories/search`

Perform hybrid search with optional metadata filters.

**Request Body**
```json
{
  "query": "string",
  "top_k": 5,
  "filters": { "key": "value" }
}
```

**Response**
```json
{
  "memories": [ { "payload": "shape" } ]
}
```

## `GET /memories/search`

Query-parameter variant without filters (`filters` JSON must be URL encoded if required).

```
GET /memories/search?query=text&top_k=5
```

## Operational Probes (No Auth)

| Endpoint | Notes |
|----------|-------|
| `GET /stats` | JSON statistics (rate limited). |
| `GET /health`, `/healthz`, `/readyz` | Health/liveness/readiness checks. |
| `GET /metrics` | Prometheus metrics. |
| `GET /` | Landing page. |
| `GET /ping` | Simple connectivity test. |

> There are no other supported endpoints. Requests to `/store`, `/recall`, or any graph routes result in HTTP 404.
