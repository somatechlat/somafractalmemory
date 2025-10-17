---
title: "Quick-Start Tutorial"
purpose: "Hands-on walkthrough of the core `/memories` workflow using the default development stack"
audience:
  - "End users"
  - "Product managers"
last_updated: "2025-10-17"
---

# Quick-Start Tutorial

This tutorial assumes you completed the [installation guide](installation.md) and the Docker Compose stack is running on `http://127.0.0.1:9595` with the default token from `.env`.

> **Tip:** Export the token once to simplify subsequent commands.
> ```bash
> export SOMA_TOKEN=$(grep SOMA_API_TOKEN .env | cut -d'=' -f2)
> export API_URL=http://127.0.0.1:9595
> ```

## 1. Store a Memory
```bash
curl -s -X POST "$API_URL/memories" \
  -H "Authorization: Bearer $SOMA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "coord": "42.0,17.0",
        "memory_type": "episodic",
        "payload": {
          "title": "Launch checklist signed",
          "importance": 0.9,
          "topic": "product"
        }
      }'
```
Expected response:
```json
{"coord":"42.0,17.0","memory_type":"episodic","ok":true}
```

## 2. Retrieve the Memory
```bash
curl -s "$API_URL/memories/42.0,17.0" \
  -H "Authorization: Bearer $SOMA_TOKEN"
```
You should see the original payload embedded in the `memory` field.

## 3. Search Across Memories
```bash
curl -s -X POST "$API_URL/memories/search" \
  -H "Authorization: Bearer $SOMA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "query": "launch",
        "top_k": 3,
        "filters": { "topic": "product" }
      }' | jq
```
If the memory exists, it will appear in the `memories` array. Use the GET variant with query parameters if preferred:
```bash
curl -s "$API_URL/memories/search?query=launch&top_k=3" \
  -H "Authorization: Bearer $SOMA_TOKEN"
```

## 4. Delete the Memory
```bash
curl -s -X DELETE "$API_URL/memories/42.0,17.0" \
  -H "Authorization: Bearer $SOMA_TOKEN"
```
A successful deletion returns:
```json
{"coord":"42.0,17.0","deleted":true}
```

## 5. Check Service Health
The following endpoints are intentionally unauthenticated for operators:
```bash
curl -s "$API_URL/health"
curl -s "$API_URL/stats"
curl -s "$API_URL/metrics" | head -n 5
```

### Kubernetes Note
If you deployed via Helm, replace `http://127.0.0.1:9595` with your service address (default service port: `9595`).

## Next Steps
- [Explore feature guides](features/)
- [Review the FAQ](faq.md)
- [Dive into operational docs](../technical-manual/index.md)
