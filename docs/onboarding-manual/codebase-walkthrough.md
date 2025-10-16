# Codebase Walkthrough

## Repository Structure

```
somafractalmemory/
├─ somafractalmemory/     # Main package
│  ├─ core.py            # Core memory system
│  ├─ http_api.py        # REST API
│  ├─ grpc_server.py     # gRPC server
│  └─ implementations/   # Storage backends
├─ common/               # Shared utilities
│  ├─ config/           # Configuration
│  └─ utils/            # Helper functions
├─ tests/               # Test suite
└─ docs/                # Documentation
```

## Key Components

### 1. Core Memory System (`core.py`)

Handles:
- Memory storage
- Importance calculation
- Vector embeddings
- Memory retrieval

```python
class SomaFractalMemoryEnterprise:
    """Main memory system implementation."""
    def store(self, content: str, importance: float) -> str:
        """Store new memory with importance score."""
        pass

    def recall(self, memory_id: str) -> dict:
        """Retrieve specific memory by ID."""
        pass
```

### 2. HTTP API (`http_api.py`)

Provides:
- REST endpoints
- Authentication
- Request validation
- Error handling

### 3. Storage Layer (`implementations/`)

#### Key-Value Store
```python
class PostgresKeyValueStore:
    """PostgreSQL-based key-value storage."""
    pass

class RedisKeyValueStore:
    """Redis-based key-value storage."""
    pass
```

#### Vector Store
```python
class QdrantVectorStore:
    """Qdrant-based vector storage."""
    pass
```

## Data Flow

1. **Memory Storage**
   ```
   Client → HTTP API → Core → Storage Layer
   ```

2. **Memory Retrieval**
   ```
   Client → HTTP API → Core → Storage Layer
   ```

## Important Files

| File | Purpose | Key Classes |
|------|---------|-------------|
| `core.py` | Memory system implementation | `SomaFractalMemoryEnterprise` |
| `http_api.py` | REST API endpoints | `FastAPI` routes |
| `factory.py` | System initialization | `create_memory_system` |
| `settings.py` | Configuration management | `SMFSettings` |

## Configuration

### Environment Variables

```bash
SOMA_API_TOKEN=secret
SOMA_POSTGRES_URL=postgresql://user:pass@host/db
SOMA_REDIS_HOST=redis
SOMA_QDRANT_URL=http://qdrant:6333
```

### Configuration Files

```yaml
# config.yaml
namespace: default
vector_dim: 768
api_port: 9595
```

## Testing Strategy

1. **Unit Tests**
   ```python
   # test_core.py
   def test_memory_storage():
       memory = create_test_memory()
       assert memory.store("test") is not None
   ```

2. **Integration Tests**
   ```python
   # test_api.py
   async def test_api_endpoints():
       response = await client.post("/memory")
       assert response.status_code == 200
   ```

## Common Workflows

### Adding New Feature

1. Update core implementation
2. Add API endpoint
3. Write tests
4. Update documentation

### Fixing Bug

1. Write failing test
2. Fix implementation
3. Verify fix
4. Add regression test
