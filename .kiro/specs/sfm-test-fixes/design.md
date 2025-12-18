# Design Document - SomaFractalMemory Test Fixes

## Overview

This design addresses the remaining test failures in SomaFractalMemory after the VIBE decomposition work. The primary issues are:

1. **Namespace isolation in memory_stats()** - The function currently aggregates vector counts across all Milvus collections instead of just the current namespace's collection
2. **Postgres connection pool exhaustion** - Concurrent tenant tests create too many simultaneous database connections

## Architecture

The fix involves modifications to two key areas:

```
┌─────────────────────────────────────────────────────────────┐
│                    memory_stats_op()                        │
│                  (operations/stats.py)                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              MilvusVectorStore.count()                      │
│           (implementations/milvus_vector.py)                │
│                                                             │
│  NEW: Add count() method to return collection entity count  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              PostgresKeyValueStore                          │
│           (implementations/postgres_kv.py)                  │
│                                                             │
│  FIX: Increase connection pool size and add overflow        │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. MilvusVectorStore Enhancement

Add a `count()` method to efficiently get the number of entities in the collection:

```python
def count(self) -> int:
    """Return the number of entities in the collection."""
    coll = self._Collection(self.collection_name)
    return coll.num_entities
```

### 2. stats.py Modification

Update `memory_stats_op()` to use the namespace-scoped vector count:

```python
# BEFORE (problematic):
vector_count = 0
for _ in system.vector_store.scroll():
    vector_count += 1

# AFTER (namespace-scoped):
vector_count = 0
if hasattr(system.vector_store, 'count'):
    vector_count = system.vector_store.count()
else:
    for _ in system.vector_store.scroll():
        vector_count += 1
```

### 3. PostgresKeyValueStore Connection Pool

Increase pool size and add overflow capacity:

```python
# Current (implicit defaults):
engine = create_engine(url)

# Fixed (explicit pool configuration):
engine = create_engine(
    url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

## Data Models

No changes to data models required.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing the prework, the following properties are identified:

- Properties 1.1 and 1.4 are logically equivalent (namespace isolation) - consolidate into one property
- Properties 1.2 is a specific case of namespace isolation for vectors
- Property 2.1 and 3.3 both test concurrent tenant behavior - can be combined

### Property 1: Namespace-Scoped KV Count

*For any* namespace and set of stored memories, `memory_stats()["total_memories"]` SHALL equal the count of keys matching `{namespace}:*:data` pattern in the KV store.

**Validates: Requirements 1.1, 1.4**

### Property 2: Namespace-Scoped Vector Count

*For any* namespace with a Milvus collection, `memory_stats()["vector_count"]` SHALL equal `collection.num_entities` for that namespace's collection only.

**Validates: Requirements 1.2**

### Property 3: Fresh Namespace Zero Count

*For any* freshly created namespace with no stored memories, `memory_stats()` SHALL return `{"total_memories": 0, "vector_count": 0}`.

**Validates: Requirements 1.3**

### Property 4: Concurrent Tenant Isolation

*For any* set of N concurrent tenants, each tenant's `memory_stats()` SHALL reflect only that tenant's data, with no cross-tenant leakage.

**Validates: Requirements 2.1, 2.3, 3.3**

## Error Handling

1. **Milvus collection not found**: Return 0 for vector_count with warning log
2. **Connection pool exhaustion**: SQLAlchemy will queue requests up to `max_overflow`; if exceeded, raise `TimeoutError` with clear message
3. **Invalid namespace**: Validate namespace format before operations

## Testing Strategy

### Dual Testing Approach

Both unit tests and property-based tests will be used:

- **Unit tests**: Verify specific examples and edge cases
- **Property-based tests**: Verify universal properties across random inputs

### Property-Based Testing Framework

Use `hypothesis` for property-based testing (already in project dependencies).

Each property test will:
1. Run minimum 100 iterations
2. Be tagged with the property number and requirements reference
3. Use real infrastructure (no mocks per VIBE rules)

### Test Structure

```python
# Example property test annotation format:
# **Feature: sfm-test-fixes, Property 2: Namespace-Scoped Vector Count**
# **Validates: Requirements 1.2**
@given(st.text(min_size=1, max_size=20, alphabet=string.ascii_lowercase))
@settings(max_examples=100)
def test_namespace_scoped_vector_count(namespace_suffix):
    ...
```

### Unit Tests

1. `test_memory_stats_fresh_namespace` - Verify zero counts on fresh namespace
2. `test_memory_stats_after_store` - Verify counts increase after storing
3. `test_concurrent_tenants_no_exhaustion` - Verify pool handles concurrent load
