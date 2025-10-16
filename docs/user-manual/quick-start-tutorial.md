# Quick Start Tutorial

## Introduction

This tutorial will guide you through basic operations with Soma Fractal Memory.

## Prerequisites

- [Installation completed](installation.md)
- Bearer token for authentication (default: `devtoken`)

## Step 1: First Memory Store

```bash
# Store your first memory
curl -X POST http://localhost:9595/api/v1/memory \
  -H "Authorization: Bearer devtoken" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello World", "importance": 0.8}'
```

## Step 2: Memory Retrieval

```bash
# Retrieve memories
curl http://localhost:9595/api/v1/memory/search \
  -H "Authorization: Bearer devtoken" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello", "limit": 10}'
```

## Next Steps

- [Explore advanced features](features/)
- [Read the FAQ](faq.md)
- [Review technical documentation](../technical-manual/)
