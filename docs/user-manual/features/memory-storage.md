---
title: "Memory Storage in SomaFractalMemory"
purpose: "Learn how to store and manage memories in SomaFractalMemory"
audience:
  - "Application Developers"
  - "End Users"
prerequisites:
  - "SomaFractalMemory API access"
  - "Basic understanding of REST APIs"
version: "1.0.0"
last_updated: "2025-10-15"
review_frequency: "quarterly"
---

# Memory Storage

## Overview
SomaFractalMemory provides vector-based memory storage with importance scoring and automatic decay.

## Storage Methods

### Basic Memory Storage
```bash
curl -X POST http://localhost:9595/store \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "coord": "1.0,2.0,3.0",
    "payload": {
      "text": "Sample memory",
      "type": "episodic"
    }
  }'
```

### Bulk Memory Storage
```bash
curl -X POST http://localhost:9595/store_bulk \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "coord": "1.0,2.0,3.0",
        "payload": {
          "text": "First memory",
          "type": "episodic"
        }
      },
      {
        "coord": "4.0,5.0,6.0",
        "payload": {
          "text": "Second memory",
          "type": "semantic"
        }
      }
    ]
  }'
```

## Memory Types
- **Episodic**: Event-based memories
- **Semantic**: Fact-based memories

## Importance Scoring
Memories can include importance scores that affect recall priority:
```json
{
  "coord": "1.0,2.0,3.0",
  "payload": {
    "text": "Critical memory",
    "type": "episodic",
    "importance": 0.9
  }
}
```

## Memory Decay
The system automatically manages memory decay based on:
- Access frequency
- Importance score
- Age of memory

## Verification
Check stored memories using the stats endpoint:
```bash
curl http://localhost:9595/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Common Issues
| Problem | Solution |
|---------|----------|
| Authorization failed | Check your API token |
| Invalid coordinate format | Ensure coordinates are comma-separated floats |
| Duplicate memory | Use different coordinates or update existing memory |

## References
- [API Reference](../../development-manual/api-reference.md)
- [Memory Types Guide](memory-types.md)
- [Importance Scoring Details](importance-scoring.md)
