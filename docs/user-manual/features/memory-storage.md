---
title: Memory Storage Workflow---
purpose: 'title: "Memory Storage in SomaFractalMemory"'
audience:
- End Users
last_updated: '2025-10-16'
---


# Memory Storage Workflow---

title: "Memory Storage in SomaFractalMemory"

Use this guide whenever you need to capture durable facts for retrievers, copilots, or automation.purpose: "Learn how to store and manage memories in SomaFractalMemory"

audience:

## HTTP Steps  - "Application Developers"

  - "End Users"

1. **Store** the payload.prerequisites:

     - "SomaFractalMemory API access"

   ```bash  - "Basic understanding of REST APIs"

   curl -s -X POST http://localhost:9595/memories \version: "1.0.0"

     -H "Content-Type: application/json" \last_updated: "2025-10-15"

     -H "Authorization: Bearer ${SOMA_API_TOKEN}" \review_frequency: "quarterly"

     -d '{---

           "coord": "100.0,200.0",

           "memory_type": "semantic",# Memory Storage

           "payload": {

             "summary": "Product brief signed",## Overview

             "tags": ["product", "launch"],SomaFractalMemory provides vector-based memory storage with importance scoring and automatic decay.

             "importance": 0.8

           }## Storage Methods

         }'

   ```### Basic Memory Storage

```bash

   The service responds with `{ "coord": "100.0,200.0", "memory_type": "semantic", "ok": true }`.curl -X POST http://localhost:9595/store \

  -H "Authorization: Bearer YOUR_TOKEN" \

2. **Verify** the memory exists.  -H "Content-Type: application/json" \

     -d '{

   ```bash    "coord": "1.0,2.0,3.0",

   curl -s http://localhost:9595/memories/100.0,200.0 \    "payload": {

     -H "Authorization: Bearer ${SOMA_API_TOKEN}"      "text": "Sample memory",

   ```      "type": "episodic"

    }

   The `memory` object mirrors your payload and includes recorded metadata (`coordinate`, timestamps, namespace, and memory type).  }'

```

3. **Update** behaviour by overwriting the same coordinate. Re-POSTing to `coord` `100.0,200.0` replaces the payload. This is the supported update path.

### Bulk Memory Storage

4. **Delete** once it is obsolete.```bash

   curl -X POST http://localhost:9595/store_bulk \

   ```bash  -H "Authorization: Bearer YOUR_TOKEN" \

   curl -s -X DELETE http://localhost:9595/memories/100.0,200.0 \  -H "Content-Type: application/json" \

     -H "Authorization: Bearer ${SOMA_API_TOKEN}"  -d '{

   ```    "items": [

      {

## CLI Equivalent        "coord": "1.0,2.0,3.0",

        "payload": {

```bash          "text": "First memory",

soma store --coord 100.0,200.0 --payload '{"summary": "Product brief signed"}' --type semantic          "type": "episodic"

soma get --coord 100.0,200.0        }

soma delete --coord 100.0,200.0      },

```      {

        "coord": "4.0,5.0,6.0",

The CLI shares the same validation rules and is useful for smoke tests and scripts.        "payload": {

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
