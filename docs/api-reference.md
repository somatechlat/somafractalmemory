# API Reference

Complete reference for all SomaFractalMemory API endpoints.

## Base URL

```
http://localhost:10101
```

## Authentication

All endpoints except health probes require Bearer token authentication (SOMA_API_TOKEN or `sfm_*` API key):

```
Authorization: Bearer YOUR_TOKEN
```

Set the shared token via `SOMA_API_TOKEN` environment variable or use an issued API key.

---

## Health Endpoints

### GET /healthz

Kubernetes liveness probe. Returns 200 if healthy, 503 if any backend is down.

**Response**

```json
{
    "kv_store": true,
    "vector_store": true,
    "graph_store": true
}
```

---

### GET /health

Detailed health check with service latencies and per-tenant statistics.

**Response**

```json
{
    "status": "healthy",
    "version": "0.2.0",
    "uptime_seconds": 2.537,
    "timestamp": "2025-12-24T02:58:35.587969+00:00",
    "services": [
        {
            "name": "postgresql",
            "healthy": true,
            "latency_ms": 66.43,
            "details": {"database": "somamemory"}
        },
        {
            "name": "redis",
            "healthy": true,
            "latency_ms": 41.53,
            "details": {"host": "redis", "port": 6379}
        },
        {
            "name": "milvus",
            "healthy": true,
            "latency_ms": 246.92,
            "details": {"host": "milvus", "port": "19530"}
        }
    ],
    "database": {
        "total_memories": 1,
        "episodic_memories": 1,
        "semantic_memories": 0,
        "total_graph_links": 0,
        "total_namespaces": 0
    },
    "tenants": [
        {
            "tenant": "default",
            "total_memories": 1,
            "episodic": 1,
            "semantic": 0,
            "graph_links": 0
        }
    ],
    "system": {
        "python_version": "3.10.19",
        "platform": "Linux-...",
        "hostname": "container-id",
        "process_id": 9,
        "django_settings": "somafractalmemory.settings"
    }
}
```

---

### GET /readyz

Kubernetes readiness probe.

**Response**

```json
{
    "kv_store": true,
    "vector_store": true,
    "graph_store": true
}
```

---

### GET /stats

Memory statistics for the current namespace.

**Response**

```json
{
    "total_memories": 10,
    "episodic": 7,
    "semantic": 3,
    "namespace": "api_ns"
}
```

---

### GET /ping

Simple health check.

**Response**

```json
{"ping": "pong"}
```

---

### GET /metrics

Prometheus metrics endpoint. Returns metrics in Prometheus text format.

---

## Memory Endpoints

### POST /memories

Store a new memory.

**Request Body**

```json
{
    "coord": "1.0,2.0,3.0",
    "payload": {
        "content": "Hello World",
        "type": "note"
    },
    "memory_type": "episodic"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `coord` | string | Yes | Comma-separated coordinate values |
| `payload` | object | Yes | Arbitrary JSON payload |
| `memory_type` | string | No | "episodic" (default) or "semantic" |

**Response**

```json
{
    "coord": "1.0,2.0,3.0",
    "memory_type": "episodic"
}
```

**cURL Example**

```bash
curl -X POST http://localhost:10101/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"coord": "1.0,2.0,3.0", "payload": {"content": "Hello"}, "memory_type": "episodic"}'
```

---

### GET /memories/{coord}

Retrieve a memory by coordinate.

**Path Parameters**

| Parameter | Description |
|-----------|-------------|
| `coord` | Comma-separated coordinate (e.g., "1.0,2.0,3.0") |

**Response**

```json
{
    "memory": {
        "coordinate": [1.0, 2.0, 3.0],
        "payload": {"content": "Hello World"},
        "memory_type": "episodic",
        "metadata": {},
        "importance": 0.0,
        "created_at": "2025-12-24T02:58:14.044028+00:00",
        "updated_at": "2025-12-24T02:58:14.203592+00:00"
    }
}
```

**cURL Example**

```bash
curl http://localhost:10101/memories/1.0,2.0,3.0 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### DELETE /memories/{coord}

Delete a memory by coordinate.

**Path Parameters**

| Parameter | Description |
|-----------|-------------|
| `coord` | Comma-separated coordinate |

**Response**

```json
{
    "coord": "1.0,2.0,3.0",
    "deleted": true
}
```

---

## Graph Endpoints

### POST /graph/link

Create a link between two coordinates.

**Request Body**

```json
{
    "from_coord": "1.0,2.0,3.0",
    "to_coord": "4.0,5.0,6.0",
    "link_type": "related",
    "strength": 1.0,
    "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from_coord` | string | Yes | Source coordinate |
| `to_coord` | string | Yes | Target coordinate |
| `link_type` | string | No | Relationship type |
| `strength` | float | No | Link strength (default: 1.0) |
| `metadata` | object | No | Additional metadata |

**Response**

```json
{
    "from_coord": "1.0,2.0,3.0",
    "to_coord": "4.0,5.0,6.0",
    "link_type": "related",
    "ok": true
}
```

---

### GET /graph/neighbors

Get neighbors of a coordinate.

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `coord` | string | Yes | - | Source coordinate |
| `k_hop` | int | No | 1 | Number of hops |
| `limit` | int | No | 10 | Max results |
| `link_type` | string | No | - | Filter by link type |

**Response**

```json
{
    "coord": "1.0,2.0,3.0",
    "neighbors": [
        {
            "coordinate": [4.0, 5.0, 6.0],
            "link_type": "related",
            "strength": 1.0
        }
    ]
}
```

**cURL Example**

```bash
curl "http://localhost:10101/graph/neighbors?coord=1.0,2.0,3.0&k_hop=2&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### GET /graph/path

Find shortest path between two coordinates.

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `from_coord` | string | Yes | - | Start coordinate |
| `to_coord` | string | Yes | - | End coordinate |
| `max_length` | int | No | 10 | Max path length |
| `link_type` | string | No | - | Filter by link type |

**Response**

```json
{
    "from_coord": "1.0,2.0,3.0",
    "to_coord": "7.0,8.0,9.0",
    "path": ["1.0,2.0,3.0", "4.0,5.0,6.0", "7.0,8.0,9.0"],
    "link_types": ["related", "similar"],
    "found": true
}
```

---

## Search Endpoints

### GET /memories/search

Search memories using vector similarity.

**Query Parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query text |
| `top_k` | int | No | 5 | Number of results |
| `memory_type` | string | No | - | Filter by type |

**Response**

```json
{
    "memories": [
        {
            "coordinate": [1.0, 2.0, 3.0],
            "payload": {"content": "Matching content"},
            "score": 0.95
        }
    ]
}
```

---

## Error Responses

All errors follow this format:

```json
{
    "detail": "Error message here"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (invalid input) |
| 401 | Unauthorized (missing/invalid token) |
| 404 | Not found |
| 405 | Method not allowed |
| 500 | Internal server error |
| 503 | Service unavailable |

---

## Headers

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes* | Bearer token authentication |
| `Content-Type` | Yes | `application/json` for POST/PUT |
| `X-Soma-Tenant` | No | Tenant identifier (default: "default") |

*Required for all endpoints except health probes.

### Response Headers

| Header | Description |
|--------|-------------|
| `Content-Type` | `application/json` |
| `X-Content-Type-Options` | Security header |
| `Referrer-Policy` | Security header |

---

## OpenAPI Specification

Get the full OpenAPI 3.0 specification:

```bash
curl http://localhost:10101/openapi.json
```
