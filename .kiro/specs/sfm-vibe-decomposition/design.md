# Design Document - SomaFractalMemory VIBE Decomposition

## Overview

This design addresses the decomposition of 4 monolithic files in SomaFractalMemory that violate the 500-line VIBE rule:

| File | Current Lines | Target | Reduction |
|------|---------------|--------|-----------|
| `core.py` | 1903 | <500 | 74% |
| `http_api.py` | 1530 | <500 | 67% |
| `storage.py` | 860 | <500 | 42% |
| `postgres_graph.py` | 593 | <500 | 16% |

## Architecture

### Current Structure
```
somafractalmemory/
├── core.py (1903 lines - MONOLITHIC)
├── http_api.py (1530 lines - MONOLITHIC)
├── implementations/
│   ├── storage.py (860 lines - MONOLITHIC)
│   └── postgres_graph.py (593 lines)
└── ...
```

### Target Structure
```
somafractalmemory/
├── core.py (<400 lines - orchestration only)
├── operations/
│   ├── __init__.py
│   ├── store.py (~200 lines)
│   ├── retrieve.py (~200 lines)
│   ├── search.py (~250 lines)
│   ├── delete.py (~150 lines)
│   ├── graph_ops.py (~200 lines)
│   └── stats.py (~150 lines)
├── http_api.py (<400 lines - app setup only)
├── api/
│   ├── __init__.py
│   ├── schemas.py (~300 lines)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── memory.py (~200 lines)
│   │   ├── search.py (~150 lines)
│   │   ├── health.py (~100 lines)
│   │   └── admin.py (~100 lines)
│   └── dependencies.py (~100 lines)
├── implementations/
│   ├── storage.py (<200 lines - base only)
│   ├── postgres_kv.py (~300 lines)
│   ├── milvus_vector.py (~300 lines)
│   └── postgres_graph.py (<500 lines)
└── ...
```

## Components and Interfaces

### 1. Core Operations Module (`operations/`)

Extract methods from `SomaFractalMemoryEnterprise` class:

| Module | Methods to Extract |
|--------|-------------------|
| `store.py` | `store_memory`, `store`, `_fast_append`, `store_memories_bulk` |
| `retrieve.py` | `retrieve`, `retrieve_memories`, `get_all_memories` |
| `search.py` | `recall`, `hybrid_recall`, `keyword_search`, `_fast_search` |
| `delete.py` | `delete`, `forget`, `delete_many`, `_remove_vector_entries` |
| `graph_ops.py` | `link_memories`, `get_linked_memories`, `find_shortest_path` |
| `stats.py` | `memory_stats`, `summarize_memories`, `get_recent`, `get_important` |

### 2. API Module (`api/`)

Extract from `http_api.py`:

| Module | Content |
|--------|---------|
| `schemas.py` | All Pydantic models (MemoryStoreRequest, etc.) |
| `routes/memory.py` | `/store`, `/retrieve`, `/delete` endpoints |
| `routes/search.py` | `/search`, `/hybrid-search` endpoints |
| `routes/health.py` | `/health`, `/healthz` endpoints |
| `routes/admin.py` | Admin endpoints |
| `dependencies.py` | FastAPI dependencies, auth |

### 3. Storage Implementations

Extract from `storage.py`:

| Module | Content |
|--------|---------|
| `postgres_kv.py` | `PostgresKeyValueStore` class |
| `milvus_vector.py` | `MilvusVectorStore` class |
| `storage.py` | Base utilities, shared code |

## Data Models

No changes to data models - this is a structural refactoring only.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: API Endpoint Preservation
*For any* HTTP request to the API, the response after decomposition SHALL be identical to the response before decomposition.
**Validates: Requirements 2.2**

### Property 2: Store-Retrieve Round Trip
*For any* valid memory payload, storing then retrieving SHALL return the same payload.
**Validates: Requirements 1.2**

### Property 3: Import Consistency
*For any* module in the decomposed structure, importing SHALL not raise ImportError or circular import errors.
**Validates: Requirements 1.3, 2.3, 3.2**

### Property 4: Test Suite Preservation
*For any* existing test, the test SHALL pass after decomposition without modification.
**Validates: Requirements 1.4, 2.4, 3.4, 4.3**

## Error Handling

- Maintain existing error handling patterns
- No new exception types needed
- Preserve all existing error messages for API compatibility

## Testing Strategy

### Unit Tests
- Verify each extracted module can be imported independently
- Verify method signatures are preserved

### Property-Based Tests
- Use `hypothesis` library for property testing
- Test round-trip properties for store/retrieve
- Test API response consistency

### Integration Tests
- Run existing test suite without modification
- All tests must pass after decomposition
