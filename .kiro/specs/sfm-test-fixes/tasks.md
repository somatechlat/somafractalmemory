# Implementation Plan - SomaFractalMemory Test Fixes

## Overview

Fix remaining test failures related to namespace isolation in memory_stats() and Postgres connection pool exhaustion.

**Target:** All tests pass with zero failures

---

## Phase 1: Fix Namespace-Scoped Vector Count

- [x] 1. Add count() method to MilvusVectorStore
  - [x] 1.1 Add `count()` method to `somafractalmemory/implementations/milvus_vector.py`
    - Return `coll.num_entities` for the namespace's collection
    - Handle collection not loaded gracefully
    - _Requirements: 1.2_
  - [x] 1.2 Add `count()` method to IVectorStore interface
    - Add abstract method signature to `somafractalmemory/interfaces/storage.py`
    - _Requirements: 1.2_

- [x] 1.3 Write property test for namespace-scoped vector count
  - **Property 2: Namespace-Scoped Vector Count**
  - **Validates: Requirements 1.2**

- [x] 2. Checkpoint - Verify count() method works
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 2: Fix memory_stats() Namespace Isolation

- [x] 3. Update memory_stats_op() to use namespace-scoped counts
  - [x] 3.1 Modify `somafractalmemory/operations/stats.py`
    - Replace scroll-based vector count with `system.vector_store.count()`
    - Remove the `vector_collections` aggregation across all collections
    - Keep only current namespace's collection in stats
    - _Requirements: 1.1, 1.2, 1.4_
  - [x] 3.2 Verify memory_stats returns correct structure
    - Ensure `total_memories`, `episodic`, `semantic`, `vector_count` are namespace-scoped
    - _Requirements: 1.1, 1.2_

- [x] 3.3 Write property test for namespace-scoped KV count
  - **Property 1: Namespace-Scoped KV Count**
  - **Validates: Requirements 1.1, 1.4**

- [x] 3.4 Write property test for fresh namespace zero count
  - **Property 3: Fresh Namespace Zero Count**
  - **Validates: Requirements 1.3**

- [x] 4. Checkpoint - Verify test_stats.py passes
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 3: Fix Postgres Connection Pool Exhaustion

- [x] 5. Increase connection pool capacity
  - [x] 5.1 Update `somafractalmemory/implementations/postgres_kv.py`
    - Add explicit pool configuration: `pool_size=10, max_overflow=20`
    - Add `pool_pre_ping=True` for connection health checks
    - Add `pool_recycle=3600` to prevent stale connections
    - _Requirements: 2.1, 2.2_
  - [x] 5.2 Update `somafractalmemory/implementations/postgres_graph.py` (if applicable)
    - Apply same pool configuration
    - _Requirements: 2.1, 2.2_

- [x] 5.3 Write property test for concurrent tenant isolation
  - **Property 4: Concurrent Tenant Isolation**
  - **Validates: Requirements 2.1, 2.3, 3.3**

- [x] 6. Checkpoint - Verify concurrent tenant test passes
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 4: Final Verification

- [x] 7. Run full test suite
  - [x] 7.1 Clean infrastructure
    - Flush Redis: `redis-cli -h localhost -p 40022 FLUSHALL`
    - Reset Postgres schema if needed
    - _Requirements: 3.1, 3.2_
  - [x] 7.2 Run all tests
    - `uv run pytest tests/ -v`
    - All tests must pass
    - _Requirements: All_
  - [x] 7.3 Verify specific failing tests
    - `test_stats.py::test_memory_stats_counts` - MUST PASS
    - `test_deep_integration.py::TestTenantIsolation::test_concurrent_tenants_no_leakage` - MUST PASS
    - _Requirements: 1.3, 2.3_

- [x] 8. Final Checkpoint - All tests passing
  - Ensure all tests pass, ask the user if questions arise.
  - Update VIBE_VIOLATIONS_2025-12-17.md if needed
