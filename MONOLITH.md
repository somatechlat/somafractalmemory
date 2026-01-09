# Monolith Agent Integration

This branch (`monolith-agent`) documents SomaFractalMemory's integration with the SOMA Monolith deployment.

## Overview

In the Monolith Agent architecture, FractalMemory is **embedded directly** in the Agent container rather than running as a separate service.

## What Changes

| Aspect | Distributed (main branch) | Monolith (this branch) |
|--------|--------------------------|------------------------|
| Deployment | Separate container | Embedded in Agent |
| Communication | HTTP API | Direct Python import |
| Latency | ~8ms per call | ~0.1ms per call |
| Scaling | Independent | Scales with Agent |

## Integration Points

The `soma_monolith/memory.py` module in `somaAgent01` provides direct access to:

```python
from fractal_memory.service import FractalMemoryService
from fractal_memory.stores.milvus_store import MilvusVectorStore
from fractal_memory.stores.redis_store import RedisKVStore
```

## External Dependencies

Even in Monolith mode, FractalMemory still needs:
- **Milvus** (vector database) - runs as separate container
- **Redis** (KV store) - runs as separate container

These remain network calls but are inherently heavyweight operations.

## Development

- Continue developing FractalMemory normally
- The Monolith Dockerfile copies this package directly
- No code changes needed in FractalMemory

## Building

```bash
# From parent directory containing all 3 repos
cd somaAgent01
./scripts/build_monolith.sh
```

See `somaAgent01/Dockerfile.monolith` for the full build process.
