# Quick Start Tutorial

## Introduction

This tutorial will guide you through basic operations with Soma Fractal Memory.

## Prerequisites

- [Installation completed](installation.md)
- Bearer token for authentication (default: `devtoken`)

## Step 1: First Memory Store

**Note:** API runs on port **9595** - the PUBLIC API ENTRY POINT. For Kubernetes, use port **9393**.

```bash
# Store your first memory (use port 9595 - public entry point)
curl -X POST http://localhost:9595/api/v1/memory \
  -H "Authorization: Bearer devtoken" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello World", "importance": 0.8}'

# Or for Kubernetes deployment (use port 9393):
# curl -X POST http://localhost:9393/api/v1/memory \
```

## Step 2: Memory Retrieval

```bash
# Retrieve memories (use port 9595 - public entry point)
curl http://localhost:9595/api/v1/memory/search \
  -H "Authorization: Bearer devtoken" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello", "limit": 10}'

# Or for Kubernetes deployment (use port 9393):
# curl http://localhost:9393/api/v1/memory/search \
```

## Next Steps

- [Explore advanced features](features/)
- [Read the FAQ](faq.md)
- [Review technical documentation](../technical-manual/)
