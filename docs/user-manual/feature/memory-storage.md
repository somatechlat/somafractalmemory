---
title: "Memory Storage Guide"
purpose: "Guide users through storing memories in SomaFractalMemory"
audience:
  - "Primary: End-Users"
  - "Secondary: Developers"
prerequisites:
  - "SomaFractalMemory installed"
  - "API token configured"
version: "1.0.0"
last_updated: "2025-10-15"
review_frequency: "quarterly"
---

# Memory Storage Guide

## Purpose
Learn how to store new memories in SomaFractalMemory effectively.

## Prerequisites
- SomaFractalMemory installed and running
- API token configured
- Basic understanding of JSON format

## Storing a Memory

### Basic Memory Storage
1. Create a memory payload:
   ```json
   {
     "coord": "1.0,2.0,3.0",
     "payload": {
       "text": "Example memory content",
       "type": "note"
     }
   }
   ```

2. Store using the API:
   ```bash
   curl -X POST http://localhost:9595/store \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer your-token" \
     -d '{"coord": "1.0,2.0,3.0", "payload": {"text": "Example memory", "type": "note"}}'
   ```

### Verification
Check that your memory was stored:
```bash
curl -X POST http://localhost:9595/recall \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{"query": "Example memory", "top_k": 1}'
```

Expected output:
```json
{
  "matches": [
    {
      "text": "Example memory",
      "type": "note",
      "coordinate": [1.0, 2.0, 3.0]
    }
  ]
}
```

## Common Errors
| Symptom | Cause | Solution |
|---------|-------|----------|
| 401 Unauthorized | Missing or invalid token | Check your API token configuration |
| 400 Bad Request | Invalid coordinate format | Ensure coordinates are comma-separated numbers |
| Connection refused | Service not running | Start the SomaFractalMemory service |

## Advanced Usage
- [Bulk Storage Guide](./bulk-storage.md)
- [Memory Types Guide](./memory-types.md)
- [Memory Importance Guide](./importance-scoring.md)

## References
- [API Reference](../development-manual/api-reference.md)
- [Memory Model Specification](../technical-manual/memory-model.md)

---
*Was this document helpful? [Rate this page](feedback-url)*
