---
title: "Memory Search Workflow"
purpose: "SomaFractalMemory provides a single hybrid search surface which combines vector similarity with optional metadata filters."
audience:
  - "End Users"
last_updated: "2025-10-16"
---

# Memory Search Workflow

SomaFractalMemory provides a single hybrid search surface which combines vector similarity with optional metadata filters.

## HTTP API

### JSON Body Search

```bash
curl -s -X POST http://localhost:9595/memories/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SOMA_API_TOKEN}" \
  -d '{
        "query": "product launch",
        "top_k": 5,
        "filters": {
          "topic": "product",
          "memory_type": "semantic"
        }
      }'
```

**Response**

```json
{
  "memories": [
    {
      "summary": "Product brief signed",
      "topic": "product",
      "memory_type": "semantic"
    }
  ]
}
```

### Query Parameter Search

```bash
curl -s "http://localhost:9595/memories/search?query=launch&top_k=5" \
  -H "Authorization: Bearer ${SOMA_API_TOKEN}"
```

Use the GET variant for scripting or when you cannot send a JSON body. Metadata filtering is only available on the POST route.

## CLI

```bash
soma search --query "product launch" --top-k 5 --filters '{"topic": "product"}'
```

The CLI returns a JSON array of payloads; parse it with `jq` or Python as required.

## Tips

- Keep coordinates stable to enable idempotent updates.
- If you need audit-grade traceability, persist the coordinate returned from the store response alongside your business object.
- Public operational endpoints (`/health`, `/readyz`, `/metrics`) remain unauthenticated for monitoring—do not include sensitive payloads in them.
