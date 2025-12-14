---
inclusion: always
---

# Coding Standards

## Vibe Coding Rules (Enforced)

This project follows strict "Vibe Coding Rules" - see `VIBE_CODING_RULES.md` for full details.

### Core Principles

1. **NO BULLSHIT** - No mocks, no placeholders, no fake implementations, no TODOs
2. **CHECK FIRST, CODE SECOND** - Review existing architecture before changes
3. **NO UNNECESSARY FILES** - Modify existing files when possible
4. **REAL IMPLEMENTATIONS ONLY** - Production-grade code always
5. **DOCUMENTATION = TRUTH** - Verify from official docs, never invent APIs
6. **COMPLETE CONTEXT REQUIRED** - Understand full flow before modifying
7. **REAL DATA, REAL SERVERS** - Use actual services, not mocks

### Forbidden Patterns

- Shims, fallbacks, bypass routes
- Hardcoded values in production code
- Stubs or placeholder functions
- `TODO`, `FIXME`, `implement later` comments
- Mocking real services in production paths

## Python Style

- **Python 3.10+** required
- **Line length**: 100 characters
- **Formatter**: Black + Ruff
- **Type hints**: Required for public APIs
- **Imports**: isort with `somafractalmemory` as first-party

## Code Organization

```
somafractalmemory/
├── interfaces/      # Abstract base classes (IKeyValueStore, etc.)
├── implementations/ # Concrete implementations
├── config/          # Configuration modules
├── core.py          # Main SomaFractalMemoryEnterprise class
├── factory.py       # Factory functions
├── http_api.py      # FastAPI routes
└── serialization.py # JSON serialization
```

## Interface-First Design

All storage backends implement interfaces from `somafractalmemory/interfaces/`:

- `IKeyValueStore` - Key-value operations (get, set, delete, scan_iter, lock)
- `IVectorStore` - Vector operations (upsert, search, scroll, delete)
- `IGraphStore` - Graph operations (add_link, find_shortest_path)

When adding new backends, implement the appropriate interface.

## Error Handling

- Use custom exceptions from `core.py`: `SomaFractalMemoryError`, `DeleteError`, `KeyValueStoreError`, `VectorStoreError`
- Log warnings for recoverable errors, raise for fatal ones
- Never silently swallow exceptions in production paths

## Logging

Use `structlog` for structured logging:

```python
from structlog import get_logger
logger = get_logger()

logger.info("Operation completed", coordinate=coord, duration_ms=elapsed)
logger.warning("Fallback triggered", error=str(exc))
```
