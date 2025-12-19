# Implementation Plan

## Phase 1: Dead Code Removal (SomaBrain)

- [x] 1. Remove dead planner modules from SomaBrain
  - [x] 1.1 Delete `somabrain/somabrain/services/planning_service.py`
    - Confirmed never imported by any module
    - _Requirements: 2.2, 4.1_
  - [x] 1.2 Delete `somabrain/somabrain/cognitive/planning.py`
    - Confirmed never imported by any module
    - _Requirements: 2.3, 4.1_
  - [x] 1.3 Write property test verifying dead code removal
    - **Property 2: Dead Code Elimination**
    - **Validates: Requirements 4.1, 2.2, 2.3**

## Phase 2: Qdrant Removal (SomaFractalMemory)

- [x] 2. Remove deprecated Qdrant implementation
  - [x] 2.1 Delete `somafractalmemory/somafractalmemory/implementations/qdrant_vector.py`
    - Architecture decision: Milvus-only
    - _Requirements: 1.1_
  - [x] 2.2 Remove QdrantVectorStore from `implementations/__init__.py`
    - Remove import and __all__ entry
    - _Requirements: 1.3_
  - [x] 2.3 Remove QdrantVectorStore from `implementations/storage.py`
    - Remove import and __all__ entry
    - _Requirements: 1.3_
  - [x] 2.4 Update tests that reference Qdrant to use Milvus
    - `tests/test_fast_core_math.py` - uses QdrantVectorStore
    - `tests/test_bulk_store.py` - references qdrant config
    - `tests/test_versioning_roundtrip.py` - references qdrant config
    - _Requirements: 1.2_
  - [x] 2.5 Update conftest.py to remove Qdrant references
    - Remove Qdrant from service detection comments
    - _Requirements: 1.2_
  - [x] 2.6 Write property test verifying Milvus-only operations
    - **Property 5: Vector Store Consistency**
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 3. Checkpoint - Make sure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: Exception Handling Cleanup

- [x] 4. Fix silent exception swallowing patterns
  - [x] 4.1 Audit and fix `somafractalmemory/somafractalmemory/implementations/batched_store.py`
    - Multiple `except Exception: pass` patterns
    - Add DEBUG logging with context
    - _Requirements: 3.1, 3.2_
  - [x] 4.2 Audit and fix `somafractalmemory/somafractalmemory/implementations/qdrant_vector.py`
    - Note: This file will be deleted in Phase 2, skip if already removed
    - _Requirements: 3.1, 3.2_
  - [x] 4.3 Audit and fix `somafractalmemory/somafractalmemory/implementations/milvus_vector.py`
    - `except Exception: pass` patterns in count() and setup()
    - Add DEBUG logging with context
    - _Requirements: 3.1, 3.2_
  - [x] 4.4 Audit and fix `somafractalmemory/somafractalmemory/operations/search.py`
    - `except Exception: pass` patterns
    - Add DEBUG logging with context
    - _Requirements: 3.1, 3.2_
  - [x] 4.5 Audit and fix `somafractalmemory/somafractalmemory/operations/store.py`
    - `except Exception: pass` patterns
    - Add DEBUG logging with context
    - _Requirements: 3.1, 3.2_
  - [x] 4.6 Write property test verifying exception logging
    - **Property 3: Exception Logging Completeness**
    - **Validates: Requirements 3.1, 3.2**

- [x] 5. Checkpoint - Make sure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Documentation and Type Annotations

- [x] 6. Document type: ignore comments
  - [x] 6.1 Add explanations to type: ignore comments in SomaFractalMemory
    - `implementations/postgres_kv.py` - Union type narrowing
    - `implementations/milvus_vector.py` - Milvus SDK variance
    - `http_api.py` - Optional Redis dependency
    - `serialization.py` - Optional numpy
    - _Requirements: 7.1_
  - [x] 6.2 Add explanations to type: ignore comments in SomaBrain
    - `milvus_client.py` - Optional pymilvus
    - `jobs/milvus_reconciliation.py` - Dynamic imports
    - `db/models/outbox.py` - SQLAlchemy compat
    - _Requirements: 7.1_
  - [x] 6.3 Write property test verifying type: ignore documentation
    - **Property 7: Type Ignore Documentation**
    - **Validates: Requirements 7.1**

## Phase 5: Final Verification

- [x] 7. Run full test suite and verify compliance
  - [x] 7.1 Run pytest on SomaFractalMemory
    - All tests must pass
    - _Requirements: All_
  - [x] 7.2 Run pytest on SomaBrain
    - All tests must pass
    - _Requirements: All_
  - [x] 7.3 Update violations.md reports
    - Reflect completed remediation
    - _Requirements: All_

- [x] 8. Final Checkpoint - Make sure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
