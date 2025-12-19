# Design Document: Production Readiness Audit

## Overview

This design document outlines the architectural changes required to bring both SomaFractalMemory and SomaBrain repositories to production-grade quality. The audit identified several categories of issues that need remediation:

1. **Dead Code**: Unused modules and functions that add maintenance burden
2. **Duplicate Implementations**: Multiple modules serving the same purpose
3. **Deprecated Code**: Qdrant implementation that should be removed
4. **Silent Failures**: Exception handling that swallows errors without logging
5. **Configuration Inconsistency**: Direct os.environ access instead of Settings

## Architecture

### Current State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SomaBrain Planning Architecture                    │
│                                  (CURRENT - MESSY)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ cognitive.py    │    │ plan_engine.py  │    │ planning_service│         │
│  │ /plan/suggest   │───▶│ PlanEngine      │    │ .py (DEAD)      │         │
│  │ /act            │    │                 │    │ make_plan()     │         │
│  └─────────────────┘    └────────┬────────┘    └─────────────────┘         │
│                                  │                                          │
│                    ┌─────────────┴─────────────┐                            │
│                    ▼                           ▼                            │
│           ┌─────────────────┐         ┌─────────────────┐                  │
│           │ planner.py      │         │ planner_rwr.py  │                  │
│           │ BFS traversal   │         │ RWR traversal   │                  │
│           └─────────────────┘         └─────────────────┘                  │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ cognitive/      │    │ context/        │    │ oak/            │         │
│  │ planning.py     │    │ planner.py      │    │ planner.py      │         │
│  │ (DEAD CODE)     │    │ ContextPlanner  │    │ plan_for_tenant │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Target State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SomaBrain Planning Architecture                    │
│                                  (TARGET - CLEAN)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ cognitive.py    │                                                        │
│  │ /plan/suggest   │───────────────────┐                                   │
│  │ /act            │                   │                                   │
│  └─────────────────┘                   │                                   │
│                                        ▼                                   │
│                              ┌─────────────────┐                           │
│                              │ plan_engine.py  │                           │
│                              │ PlanEngine      │◀──── Single Entrypoint    │
│                              │ (Unified)       │                           │
│                              └────────┬────────┘                           │
│                                       │                                    │
│                    ┌──────────────────┼──────────────────┐                 │
│                    ▼                  ▼                  ▼                 │
│           ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │
│           │ planner.py      │ │ planner_rwr.py  │ │ context/        │      │
│           │ BFS Algorithm   │ │ RWR Algorithm   │ │ planner.py      │      │
│           │ (Pure Function) │ │ (Pure Function) │ │ ContextPlanner  │      │
│           └─────────────────┘ └─────────────────┘ └─────────────────┘      │
│                                                                             │
│                              ┌─────────────────┐                           │
│                              │ oak/planner.py  │                           │
│                              │ plan_for_tenant │◀──── Oak-Specific         │
│                              │ (Separate Path) │                           │
│                              └─────────────────┘                           │
│                                                                             │
│  REMOVED:                                                                   │
│  ✗ services/planning_service.py (dead code)                                │
│  ✗ cognitive/planning.py (dead code)                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### SomaFractalMemory Vector Store Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SomaFractalMemory Vector Store Architecture              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CURRENT:                              TARGET:                              │
│  ┌─────────────────┐                   ┌─────────────────┐                 │
│  │ IVectorStore    │                   │ IVectorStore    │                 │
│  │ (Interface)     │                   │ (Interface)     │                 │
│  └────────┬────────┘                   └────────┬────────┘                 │
│           │                                     │                          │
│     ┌─────┴─────┐                               │                          │
│     ▼           ▼                               ▼                          │
│  ┌──────┐  ┌──────┐                        ┌──────┐                        │
│  │Milvus│  │Qdrant│ ◀── REMOVE             │Milvus│ ◀── ONLY               │
│  └──────┘  └──────┘                        └──────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Planning Components (SomaBrain)

| Component | Location | Purpose | Action |
|-----------|----------|---------|--------|
| PlanEngine | `services/plan_engine.py` | Unified planning entrypoint | KEEP - Primary interface |
| plan_from_graph | `planner.py` | BFS graph traversal | KEEP - Algorithm implementation |
| rwr_plan | `planner_rwr.py` | RWR graph traversal | KEEP - Algorithm implementation |
| ContextPlanner | `context/planner.py` | Utility-based scoring | KEEP - Different purpose |
| plan_for_tenant | `oak/planner.py` | Oak option ranking | KEEP - Oak-specific |
| planning_service | `services/planning_service.py` | Wrapper functions | REMOVE - Dead code |
| Planner | `cognitive/planning.py` | Multi-step planner | REMOVE - Dead code |

### Vector Store Components (SomaFractalMemory)

| Component | Location | Purpose | Action |
|-----------|----------|---------|--------|
| MilvusVectorStore | `implementations/milvus_vector.py` | Production vector store | KEEP - Primary |
| QdrantVectorStore | `implementations/qdrant_vector.py` | Deprecated vector store | REMOVE - Deprecated |

## Data Models

No changes to data models are required. This audit focuses on code organization and cleanup.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Planning Entrypoint Consistency
*For any* planning request, the system SHALL route through PlanEngine as the single entrypoint, ensuring consistent metrics, logging, and error handling.
**Validates: Requirements 2.1**

### Property 2: Dead Code Elimination
*For any* Python module in the codebase, if the module is not imported by any other module (directly or transitively), the module SHALL be removed or documented as intentionally standalone.
**Validates: Requirements 4.1, 2.2, 2.3**

### Property 3: Exception Logging Completeness
*For any* exception caught in production code, the exception SHALL be logged at minimum DEBUG level with context about the operation that failed.
**Validates: Requirements 3.1, 3.2**

### Property 4: Configuration Access Consistency
*For any* configuration value accessed in production code, the access SHALL use the centralized Settings class rather than direct os.environ access.
**Validates: Requirements 5.1, 5.2**

### Property 5: Vector Store Consistency
*For any* vector operation (upsert, search, delete, scroll), the system SHALL use MilvusVectorStore as the only vector backend.
**Validates: Requirements 1.1, 1.2, 1.3**

### Property 6: File Size Constraint
*For any* production Python file (excluding tests), the file SHALL contain fewer than 500 lines of code, or be documented as a justified exception.
**Validates: Requirements 6.1**

### Property 7: Type Ignore Documentation
*For any* `# type: ignore` comment in the codebase, the comment SHALL include an explanation of why type checking is suppressed.
**Validates: Requirements 7.1**

## Error Handling

### Exception Handling Pattern

All exception handling SHALL follow this pattern:

```python
# CORRECT - Log with context
try:
    result = operation()
except SpecificException as exc:
    logger.warning("Operation failed", operation="name", error=str(exc))
    # Handle or re-raise

# INCORRECT - Silent swallowing
try:
    result = operation()
except Exception:
    pass  # NEVER DO THIS
```

### Custom Exception Hierarchy

```python
# Base exception for SomaFractalMemory
class SomaFractalMemoryError(Exception):
    pass

class VectorStoreError(SomaFractalMemoryError):
    pass

class KeyValueStoreError(SomaFractalMemoryError):
    pass

# Base exception for SomaBrain
class SomaBrainError(Exception):
    pass

class PlanningError(SomaBrainError):
    pass
```

## Testing Strategy

### Dual Testing Approach

This audit requires both unit tests and property-based tests:

1. **Unit Tests**: Verify specific examples of dead code removal and configuration migration
2. **Property-Based Tests**: Verify universal properties like exception logging and configuration access

### Property-Based Testing Library

- **Library**: `hypothesis` (already used in both projects)
- **Minimum Iterations**: 100 per property test

### Test Categories

| Category | Purpose | Example |
|----------|---------|---------|
| Dead Code Detection | Verify removed modules don't exist | `test_planning_service_removed` |
| Import Graph Analysis | Verify no orphaned modules | `test_no_orphaned_modules` |
| Exception Logging | Verify all exceptions are logged | `test_exception_logging_property` |
| Configuration Access | Verify Settings usage | `test_config_access_property` |
| Vector Store | Verify Milvus-only operations | `test_vector_store_milvus_only` |

### Test Annotations

Each property-based test SHALL be annotated with:
```python
# **Feature: production-readiness-audit, Property 3: Exception Logging Completeness**
# **Validates: Requirements 3.1, 3.2**
```
