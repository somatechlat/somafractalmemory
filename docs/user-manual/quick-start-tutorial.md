---
title: "Quick-Start Tutorial# Quick Start Tutorial"
purpose: "This tutorial demonstrates the complete `/memories` lifecycle using the HTTP API."
audience:
  - "End Users"
last_updated: "2025-10-16"
---

# Quick-Start Tutorial# Quick Start Tutorial



This tutorial demonstrates the complete `/memories` lifecycle using the HTTP API. It assumes you followed the [installation guide](installation.md) and the service is running on `http://localhost:9595` with the token `local-dev-token`.## Introduction



All requests must include the `Authorization: Bearer local-dev-token` header unless stated otherwise.This tutorial will guide you through basic operations with Soma Fractal Memory.



## 1. Store a Memory## Prerequisites



```bash- [Installation completed](installation.md)

curl -s -X POST http://localhost:9595/memories \- Bearer token for authentication (default: `devtoken`)

  -H "Content-Type: application/json" \

  -H "Authorization: Bearer local-dev-token" \## Step 1: First Memory Store

  -d '{

        "coord": "42.0,17.0",**Note:** API runs on port **9595** - the PUBLIC API ENTRY POINT. For Kubernetes, use port **9393**.

        "memory_type": "episodic",

        "payload": {```bash

          "title": "Launch checklist signed",# Store your first memory (use port 9595 - public entry point)

          "importance": 0.9,curl -X POST http://localhost:9595/api/v1/memory \

          "topic": "product"  -H "Authorization: Bearer devtoken" \

        }  -H "Content-Type: application/json" \

      }'  -d '{"content": "Hello World", "importance": 0.8}'

```

# Or for Kubernetes deployment (use port 9393):

Expected response:# curl -X POST http://localhost:9393/api/v1/memory \

```

```json

{## Step 2: Memory Retrieval

  "coord": "42.0,17.0",

  "memory_type": "episodic",```bash

  "ok": true# Retrieve memories (use port 9595 - public entry point)

}curl http://localhost:9595/api/v1/memory/search \

```  -H "Authorization: Bearer devtoken" \

  -H "Content-Type: application/json" \

## 2. Retrieve the Memory  -d '{"query": "Hello", "limit": 10}'



```bash# Or for Kubernetes deployment (use port 9393):

curl -s http://localhost:9595/memories/42.0,17.0 \# curl http://localhost:9393/api/v1/memory/search \

  -H "Authorization: Bearer local-dev-token"```

```

## Next Steps

Expected response (payload mirrors the stored JSON and includes metadata such as timestamps):

- [Explore advanced features](features/)

```json- [Read the FAQ](faq.md)

{- [Review technical documentation](../technical-manual/)

  "memory": {
    "coordinate": [42.0, 17.0],
    "payload": {
      "title": "Launch checklist signed",
      "importance": 0.9,
      "topic": "product"
    }
  }
}
```

## 3. Search Across Memories

```bash
curl -s -X POST http://localhost:9595/memories/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local-dev-token" \
  -d '{
        "query": "launch",
        "top_k": 3,
        "filters": { "topic": "product" }
      }'
```

Expected response:

```json
{
  "memories": [
    {
      "title": "Launch checklist signed",
      "importance": 0.9,
      "topic": "product"
    }
  ]
}
```

To use the GET variant:

```bash
curl -s "http://localhost:9595/memories/search?query=launch&top_k=3" \
  -H "Authorization: Bearer local-dev-token"
```

## 4. Delete the Memory

```bash
curl -s -X DELETE http://localhost:9595/memories/42.0,17.0 \
  -H "Authorization: Bearer local-dev-token"
```

Expected response:

```json
{
  "coord": "42.0,17.0",
  "deleted": true
}
```

## 5. Inspect Service Health

The following endpoints are intentionally public and remain unauthenticated for operators:

```bash
curl -s http://localhost:9595/health
curl -s http://localhost:9595/stats
curl -s http://localhost:9595/metrics | head -n 5
```

You now have the basic workflow necessary to integrate SomaFractalMemory into any product or automation.
