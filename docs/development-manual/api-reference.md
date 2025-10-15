---
title: "API Reference"
purpose: "Complete reference for SomaFractalMemory API"
audience:
  - "Application Developers"
  - "System Integrators"
prerequisites:
  - "Basic REST API knowledge"
  - "JSON and HTTP concepts"
version: "1.0.0"
last_updated: "2025-10-15"
review_frequency: "quarterly"
---

# API Reference

## Base URL
```
http://localhost:9595
```

## Authentication
All endpoints require Bearer token authentication:
```http
Authorization: Bearer YOUR_API_TOKEN
```

## Memory Operations

### Store Memory
```http
POST /store
Content-Type: application/json

{
  "coord": "1.0,2.0,3.0",
  "payload": {
    "text": "Sample memory",
    "type": "episodic",
    "metadata": {
      "source": "user_input",
      "timestamp": "2025-10-15T12:00:00Z"
    }
  },
  "importance": 0.8
}
```

#### Response
```json
{
  "status": "success",
  "id": "mem_123abc"
}
```

### Bulk Store
```http
POST /store_bulk
Content-Type: application/json

{
  "items": [
    {
      "coord": "1.0,2.0,3.0",
      "payload": {
        "text": "First memory"
      }
    },
    {
      "coord": "4.0,5.0,6.0",
      "payload": {
        "text": "Second memory"
      }
    }
  ]
}
```

### Recall Memory
```http
POST /recall
Content-Type: application/json

{
  "query": "Sample memory",
  "top_k": 5,
  "filters": {
    "type": "episodic"
  }
}
```

#### Response
```json
{
  "matches": [
    {
      "text": "Sample memory",
      "coord": [1.0, 2.0, 3.0],
      "score": 0.95
    }
  ]
}
```

## Graph Operations

### Create Link
```http
POST /link
Content-Type: application/json

{
  "from_coord": "1.0,2.0,3.0",
  "to_coord": "4.0,5.0,6.0",
  "type": "related",
  "weight": 1.0
}
```

### Find Neighbors
```http
GET /neighbors?coord=1.0,2.0,3.0
```

### Find Path
```http
GET /shortest_path?frm=1.0,2.0,3.0&to=7.0,8.0,9.0
```

## System Operations

### Get Stats
```http
GET /stats
```

#### Response
```json
{
  "memory_count": 1000,
  "edge_count": 2500,
  "vector_dimension": 128
}
```

### Health Check
```http
GET /health
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid coordinate format",
  "code": "INVALID_COORD"
}
```

### 401 Unauthorized
```json
{
  "error": "Invalid or missing token",
  "code": "AUTH_ERROR"
}
```

### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT",
  "retry_after": 60
}
```

## Rate Limits
- Store: 100 requests/minute
- Recall: 200 requests/minute
- Bulk operations: 10 requests/minute

## Best Practices
1. Use batch operations for multiple items
2. Include relevant metadata
3. Handle rate limits with exponential backoff
4. Implement proper error handling

## References
- [Getting Started Guide](../user-manual/getting-started.md)
- [Authentication Guide](authentication.md)
- [Error Codes](error-codes.md)
