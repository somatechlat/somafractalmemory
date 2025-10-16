---
title: "HTTP API Integration Guide"
purpose: "Guide users on integrating with the HTTP API"
audience: "Developers and integrators"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# HTTP API Integration Guide

## Overview

SomaFractalMemory provides a RESTful HTTP API for easy integration. This guide covers authentication, endpoints, and common usage patterns.

## Quick Start

### Authentication
```bash
# Get API token
curl -X POST http://api.somafractalmemory.com/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key"}'

# Use token in requests
curl http://api.somafractalmemory.com/memories \
  -H "Authorization: Bearer your-token"
```

## API Endpoints

### Memory Operations

<div class="api-endpoint">
<span class="api-method--post">POST</span> `/memories`

Create a new memory.
</div>

```json
{
  "content": "Memory content",
  "metadata": {
    "type": "note",
    "tags": ["important"]
  },
  "vector": [0.1, 0.2, 0.3]
}
```

<div class="api-endpoint">
<span class="api-method--get">GET</span> `/memories/{id}`

Retrieve a memory by ID.
</div>

```json
{
  "id": "mem_123",
  "content": "Memory content",
  "metadata": {
    "type": "note",
    "tags": ["important"]
  },
  "vector": [0.1, 0.2, 0.3],
  "created_at": "2025-10-16T10:00:00Z"
}
```

### Vector Search

<div class="api-endpoint">
<span class="api-method--post">POST</span> `/search/vector`

Search memories by vector similarity.
</div>

```json
{
  "vector": [0.1, 0.2, 0.3],
  "limit": 5,
  "threshold": 0.7
}
```

### Graph Operations

<div class="api-endpoint">
<span class="api-method--post">POST</span> `/memories/{id}/links`

Create links between memories.
</div>

```json
{
  "target_id": "mem_456",
  "relationship": "references",
  "metadata": {
    "strength": 0.8
  }
}
```

## Error Handling

### HTTP Status Codes
| Code | Description | Example |
|------|-------------|---------|
| 200 | Success | Operation completed |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Invalid token |
| 404 | Not Found | Memory not found |
| 500 | Server Error | Internal error |

### Error Response Format
```json
{
  "error": {
    "code": "MEMORY_NOT_FOUND",
    "message": "Memory with ID mem_123 not found",
    "details": {
      "id": "mem_123"
    }
  }
}
```

## Rate Limiting

| Plan | Rate | Burst |
|------|------|-------|
| Basic | 100/min | 200 |
| Pro | 1000/min | 2000 |
| Enterprise | Custom | Custom |

Headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1634386800
```

## Common Use Cases

### 1. Store and Retrieve
```python
import requests

# Store memory
response = requests.post(
    "http://api.somafractalmemory.com/memories",
    headers={"Authorization": "Bearer token"},
    json={
        "content": "Important note",
        "metadata": {"type": "note"}
    }
)
memory_id = response.json()["id"]

# Retrieve memory
memory = requests.get(
    f"http://api.somafractalmemory.com/memories/{memory_id}",
    headers={"Authorization": "Bearer token"}
).json()
```

### 2. Vector Search
```python
# Search similar memories
results = requests.post(
    "http://api.somafractalmemory.com/search/vector",
    headers={"Authorization": "Bearer token"},
    json={
        "vector": [0.1, 0.2, 0.3],
        "limit": 5
    }
).json()
```

### 3. Graph Operations
```python
# Create link
requests.post(
    f"http://api.somafractalmemory.com/memories/{memory_id}/links",
    headers={"Authorization": "Bearer token"},
    json={
        "target_id": "mem_456",
        "relationship": "references"
    }
)
```

## Best Practices

1. **Authentication**
   - Store tokens securely
   - Rotate tokens regularly
   - Use HTTPS always

2. **Performance**
   - Use connection pooling
   - Implement retries
   - Cache responses

3. **Error Handling**
   - Implement backoff
   - Log errors
   - Monitor rates

## SDK Examples

### Python
```python
from somafractalmemory import Client

client = Client(api_token="your-token")

# Store memory
memory = client.store(
    content="Example",
    metadata={"type": "note"}
)

# Search
results = client.search_vector(
    vector=[0.1, 0.2, 0.3],
    limit=5
)
```

### JavaScript
```javascript
import { SomaFractalMemory } from 'soma-fractalmemory';

const client = new SomaFractalMemory({
  token: 'your-token'
});

// Store memory
const memory = await client.store({
  content: 'Example',
  metadata: { type: 'note' }
});

// Search
const results = await client.searchVector({
  vector: [0.1, 0.2, 0.3],
  limit: 5
});
```

## Webhooks

### Configuration
```json
{
  "url": "https://your-domain.com/webhook",
  "events": ["memory.created", "memory.updated"],
  "secret": "webhook-secret"
}
```

### Event Types
| Event | Description |
|-------|-------------|
| memory.created | New memory created |
| memory.updated | Memory updated |
| memory.deleted | Memory deleted |
| link.created | Link created |

## Advanced Features

### Batch Operations
```http
POST /memories/batch
Content-Type: application/json

{
  "memories": [
    {
      "content": "Memory 1",
      "metadata": {"type": "note"}
    },
    {
      "content": "Memory 2",
      "metadata": {"type": "note"}
    }
  ]
}
```

### Streaming
```http
GET /memories/stream
Authorization: Bearer token
Accept: text/event-stream
```

## Monitoring

### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "cache": "healthy",
    "vector_store": "healthy"
  }
}
```

## Further Reading
- [API Reference](../../development-manual/api-reference.md)
- [Authentication Guide](authentication.md)
- [Rate Limiting](rate-limiting.md)
- [Webhooks Guide](webhooks.md)
