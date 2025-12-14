---
inclusion: manual
---

# API Reference

## Authentication

All endpoints require Bearer token authentication:
```
Authorization: Bearer <SOMA_API_TOKEN>
```

For local dev, use `devtoken`.

## Endpoints

### Health

```
GET /healthz
```
Returns 200 if API is running (no auth required).

```
GET /health
```
Returns detailed health status of all backends (requires auth).

### Memories

#### Store Memory
```
POST /memories
Content-Type: application/json

{
  "coord": "0.1,0.2,0.3",
  "payload": {"key": "value"},
  "memory_type": "episodic"
}
```

#### Retrieve Memory
```
GET /memories/{coord}
```

#### Search Memories
```
POST /memories/search
Content-Type: application/json

{
  "query": "search text",
  "top_k": 10
}
```

#### Delete Memory
```
DELETE /memories/{coord}
```

### Stats

```
GET /stats
```
Returns memory system statistics.

## Coordinate Format

Coordinates are comma-separated float values:
- `"0.1,0.2,0.3"` → `(0.1, 0.2, 0.3)`
- `"1000,1001"` → `(1000.0, 1001.0)`

## Memory Types

- `episodic` - Event-based memories
- `semantic` - Factual knowledge

## Error Responses

```json
{
  "detail": "Error message"
}
```

Common status codes:
- `400` - Invalid request (bad coord format, missing fields)
- `401` - Unauthorized (missing/invalid token)
- `404` - Memory not found
- `500` - Internal server error
- `502` - Backend service unavailable
