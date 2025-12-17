# Implementation Plan - SomaFractalMemory VIBE Decomposition

## Status: ✅ COMPLETE (2025-12-17)

All 4 monolithic files decomposed to comply with VIBE 500-line rule.

**Final Results:**
| File | Original | Current | Reduction |
|------|----------|---------|-----------|
| `core.py` | 1903 | 385 | 80% |
| `http_api.py` | 1530 | 422 | 72% |
| `storage.py` | 860 | 34 | 96% (re-export) |
| `postgres_graph.py` | 593 | 494 | 17% |

**New Modules Created:**
- `operations/` - 8 files (store, retrieve, search, delete, graph_ops, stats, lifecycle)
- `api/` - 7 files (schemas, dependencies, routes/*)
- `implementations/` - 6 files (postgres_kv, redis_kv, milvus_vector, qdrant_vector, batched_store, graph_helpers)

**Verification:**
- ✅ All ruff checks pass
- ✅ All imports work correctly
- ✅ violations.md updated

---

## Overview

Decompose 4 monolithic files to comply with VIBE 500-line rule.

**Priority Order:**
1. `core.py` (1903 lines) - CRITICAL
2. `http_api.py` (1530 lines) - CRITICAL
3. `storage.py` (860 lines) - HIGH
4. `postgres_graph.py` (593 lines) - MEDIUM

---

## Phase 1: core.py Decomposition (1903 → <500 lines) ✅ COMPLETE

- [x] 1. Create operations module structure
  - [x] 1.1 Create `somafractalmemory/operations/__init__.py` (75 lines)
  - [x] 1.2 Create `somafractalmemory/operations/store.py` (255 lines)
  - [x] 1.3 Create `somafractalmemory/operations/retrieve.py` (150 lines)

- [x] 2. Checkpoint - Imports verified ✅

- [x] 3. Extract search operations
  - [x] 3.1 Create `somafractalmemory/operations/search.py` (388 lines)
  - [x] 3.2 Create `somafractalmemory/operations/delete.py` (94 lines)

- [x] 4. Checkpoint - Search/delete verified ✅

- [x] 5. Extract graph and utility operations
  - [x] 5.1 Create `somafractalmemory/operations/graph_ops.py` (105 lines)
  - [x] 5.2 Create `somafractalmemory/operations/stats.py` (241 lines)
  - [x] 5.3 Create `somafractalmemory/operations/lifecycle.py` (304 lines)

- [x] 6. Checkpoint - All operations verified ✅

- [x] 7. Refactor core.py to use extracted modules
  - [x] 7.1 Updated `core.py` imports
  - [x] 7.2 Updated `SomaFractalMemoryEnterprise` class to delegate
  - [x] 7.3 Verified core.py is 385 lines (target: <400) ✅

- [x] 8. Checkpoint - core.py decomposition complete ✅
  - Original backed up to `core_original.py`
  - All Python files compile successfully

---

## Phase 2: http_api.py Decomposition (1530 → <500 lines) ✅ COMPLETE

- [x] 9. Create API module structure
  - [x] 9.1 Create `somafractalmemory/api/__init__.py` (60 lines)
    - Export routers and schemas
    - _Requirements: 2.3_
  - [x] 9.2 Create `somafractalmemory/api/schemas.py` (112 lines)
    - Extract all Pydantic models
    - MemoryStoreRequest, MemoryStoreResponse, etc.
    - _Requirements: 2.3_
  - [x] 9.3 Create `somafractalmemory/api/dependencies.py` (85 lines)
    - Extract FastAPI dependencies
    - Auth, settings, memory system access
    - _Requirements: 2.3_

- [x] 10. Checkpoint - Verify schemas work ✅

- [x] 11. Extract route handlers
  - [x] 11.1 Create `somafractalmemory/api/routes/__init__.py` (9 lines)
    - Export all routers
    - _Requirements: 2.2_
  - [x] 11.2 Create `somafractalmemory/api/routes/memory.py` (114 lines)
    - Extract `/store`, `/retrieve`, `/delete` endpoints
    - _Requirements: 2.2_
  - [x] 11.3 Create `somafractalmemory/api/routes/search.py` (84 lines)
    - Extract `/search`, `/hybrid-search` endpoints
    - _Requirements: 2.2_
  - [x] 11.4 Create `somafractalmemory/api/routes/health.py` (130 lines)
    - Extract `/health`, `/healthz`, `/stats` endpoints
    - _Requirements: 2.2_
  - [x] 11.5 Create `somafractalmemory/api/routes/graph.py` (358 lines)
    - Extract graph endpoints
    - _Requirements: 2.2_

- [x] 12. Checkpoint - Verify routes work ✅

- [x] 13. Refactor http_api.py
  - [x] 13.1 Update `http_api.py` to use routers
    - Import routers from api/routes
    - Register with `app.include_router()`
    - _Requirements: 2.1_
  - [x] 13.2 Verify http_api.py is under 500 lines
    - Result: 422 lines ✅
    - _Requirements: 2.1_

- [x] 14. Checkpoint - http_api.py decomposition complete ✅
  - Original: 1530 lines → Current: 422 lines (72% reduction)

---

## Phase 3: storage.py Decomposition (860 → <500 lines)

- [x] 15. Extract storage implementations
  - [x] 15.1 Create `somafractalmemory/implementations/postgres_kv.py`
    - Extract `PostgresKeyValueStore` class
    - ~300 lines
    - _Requirements: 3.2_
  - [x] 15.2 Create `somafractalmemory/implementations/milvus_vector.py`
    - Extract `MilvusVectorStore` class
    - ~300 lines
    - _Requirements: 3.3_
  - [x] 15.3 Create `somafractalmemory/implementations/redis_kv.py`
    - Extract `RedisKeyValueStore` class (if exists)
    - ~150 lines
    - _Requirements: 3.2_

- [x] 16. Checkpoint - Verify storage implementations work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Refactor storage.py
  - [x] 17.1 Update `storage.py` to re-export
    - Import from new modules
    - Re-export for backward compatibility
    - _Requirements: 3.1_
  - [x] 17.2 Verify storage.py is under 500 lines
    - Target: <200 lines (re-export layer)
    - _Requirements: 3.1_

- [x] 18. Checkpoint - Verify storage.py decomposition complete
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 4: postgres_graph.py Decomposition (593 → <500 lines)

- [x] 19. Extract graph helpers
  - [x] 19.1 Create `somafractalmemory/implementations/graph_helpers.py`
    - Extract helper functions
    - ~100 lines
    - _Requirements: 4.2_
  - [x] 19.2 Refactor `postgres_graph.py`
    - Import from graph_helpers
    - _Requirements: 4.1_
  - [x] 19.3 Verify postgres_graph.py is under 500 lines
    - Target: <500 lines
    - _Requirements: 4.1_

- [x] 20. Final Checkpoint - All decomposition complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all files under 500 lines
  - Update violations.md with results

---

## Phase 5: Verification

- [x] 21. Final verification
  - [x] 21.1 Run full test suite
    - `pytest tests/`
    - All tests must pass
    - _Requirements: 1.4, 2.4, 3.4, 4.3_
  - [x] 21.2 Verify line counts
    - `core.py` < 500 lines
    - `http_api.py` < 500 lines
    - `storage.py` < 500 lines
    - `postgres_graph.py` < 500 lines
    - _Requirements: 1.1, 2.1, 3.1, 4.1_
  - [x] 21.3 Update violations.md
    - Mark all violations as FIXED
    - _Requirements: All_
