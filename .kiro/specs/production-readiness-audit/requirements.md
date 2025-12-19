# Requirements Document

## Introduction

This specification defines the requirements for a comprehensive production-readiness audit and code pruning initiative across both SomaFractalMemory and SomaBrain repositories. The goal is to identify and eliminate architectural failures, dead code, bad patterns, and technical debt to bring both projects to production-grade quality.

Based on the comprehensive audit conducted across both repositories, this document captures the issues found and the requirements for remediation.

## Glossary

- **SomaFractalMemory (SFM)**: Enterprise-grade agentic memory system with coordinate-based storage
- **SomaBrain**: Cognitive AI runtime with planning, memory, and neuromodulation capabilities
- **VIBE Coding Rules**: Strict coding standards enforced across both projects (no mocks, no stubs, no placeholders, no TODOs)
- **Dead Code**: Code that is never executed or modules that are never imported
- **Architectural Debt**: Design decisions that create maintenance burden or inconsistency
- **Qdrant**: Vector database that was deprecated in favor of Milvus but still has code present
- **Milvus**: The standardized vector database used across both projects

## Requirements

### Requirement 1: Remove Deprecated Qdrant Implementation

**User Story:** As a maintainer, I want to remove the deprecated Qdrant vector store implementation, so that the codebase has a single, consistent vector backend (Milvus).

#### Acceptance Criteria

1. WHEN the Qdrant implementation files are removed THEN the system SHALL continue to function using only Milvus as the vector backend
2. WHEN tests reference Qdrant THEN the system SHALL update those tests to use Milvus instead
3. WHEN imports reference QdrantVectorStore THEN the system SHALL remove those imports from `__init__.py` and `storage.py`
4. WHEN documentation references Qdrant THEN the system SHALL update documentation to reflect Milvus-only architecture

### Requirement 2: Consolidate Duplicate Planner Implementations

**User Story:** As a developer, I want a single unified planning interface, so that I don't have to maintain multiple planner implementations with overlapping functionality.

#### Current State Analysis

The codebase has **6 planner-related modules** with overlapping responsibilities:

| Module | Purpose | Status |
|--------|---------|--------|
| `services/plan_engine.py` | Unified PlanEngine - orchestrates BFS/RWR | ✅ KEEP (primary entrypoint) |
| `planner.py` | BFS graph traversal implementation | ✅ KEEP (algorithm impl) |
| `planner_rwr.py` | RWR graph traversal implementation | ✅ KEEP (algorithm impl) |
| `services/planning_service.py` | Wrapper functions for BFS/RWR | ❌ DEAD CODE (never imported) |
| `context/planner.py` | ContextPlanner for utility-based scoring | ✅ KEEP (different purpose) |
| `cognitive/planning.py` | High-level multi-step planner | ❌ DEAD CODE (never imported) |
| `oak/planner.py` | Oak option ranking planner | ✅ KEEP (Oak-specific) |

#### Acceptance Criteria

1. WHEN the planning system is invoked THEN the system SHALL use the unified PlanEngine from `services/plan_engine.py`
2. WHEN `services/planning_service.py` exists THEN the system SHALL remove it as dead code (confirmed never imported)
3. WHEN `cognitive/planning.py` exists THEN the system SHALL remove it as dead code (confirmed never imported)
4. WHEN planning metrics are recorded THEN the system SHALL use a single consistent metrics interface from `metrics/planning.py`
5. WHEN BFS or RWR algorithms are needed THEN the system SHALL import them from `planner.py` and `planner_rwr.py` respectively
6. WHEN context-aware planning is needed THEN the system SHALL use `context/planner.py` ContextPlanner
7. WHEN Oak option ranking is needed THEN the system SHALL use `oak/planner.py` plan_for_tenant

### Requirement 3: Eliminate Silent Exception Swallowing

**User Story:** As an operator, I want all exceptions to be logged appropriately, so that I can diagnose production issues effectively.

#### Acceptance Criteria

1. WHEN an exception is caught and not re-raised THEN the system SHALL log the exception at minimum DEBUG level
2. WHEN a bare `except: pass` pattern exists THEN the system SHALL replace it with specific exception handling and logging
3. WHEN exception handling is added THEN the system SHALL include context about what operation failed

### Requirement 4: Remove Dead Code and Unused Modules

**User Story:** As a maintainer, I want to remove code that is never executed, so that the codebase is easier to understand and maintain.

#### Acceptance Criteria

1. WHEN a module is not imported anywhere THEN the system SHALL either remove it or document its purpose
2. WHEN a function is defined but never called THEN the system SHALL remove it
3. WHEN legacy compatibility code exists for removed features THEN the system SHALL remove that code

### Requirement 5: Standardize Configuration Access

**User Story:** As a developer, I want all configuration to flow through the centralized Settings pattern, so that configuration is consistent and testable.

#### Acceptance Criteria

1. WHEN production code accesses configuration THEN the system SHALL use the Settings class from `common/config/settings.py`
2. WHEN direct `os.environ` access exists in production code THEN the system SHALL migrate it to Settings
3. WHEN environment variable names are used THEN the system SHALL use consistent naming conventions (SOMA_* for SFM, SOMABRAIN_* for SomaBrain)

### Requirement 6: Reduce File Sizes to Under 500 Lines

**User Story:** As a maintainer, I want all production files to be under 500 lines, so that the code is modular and easy to understand.

#### Acceptance Criteria

1. WHEN a production file exceeds 500 lines THEN the system SHALL decompose it into smaller, focused modules
2. WHEN decomposition occurs THEN the system SHALL maintain backward-compatible imports
3. WHEN the main application bootstrap file (`app.py`) exceeds 500 lines THEN the system SHALL extract router registrations and middleware setup into separate modules

### Requirement 7: Document Type Ignore Comments

**User Story:** As a developer, I want all `# type: ignore` comments to be documented, so that I understand why type checking is suppressed.

#### Acceptance Criteria

1. WHEN a `# type: ignore` comment exists THEN the system SHALL include a brief explanation of why it's needed
2. WHEN type ignores are for optional dependencies THEN the system SHALL document the optional dependency pattern at module level
3. WHEN type ignores can be eliminated by better typing THEN the system SHALL fix the underlying type issue

### Requirement 8: Ensure Test Coverage for Critical Paths

**User Story:** As a QA engineer, I want property-based tests for all critical data transformations, so that correctness is verified across many inputs.

#### Acceptance Criteria

1. WHEN a serialization/deserialization function exists THEN the system SHALL have a round-trip property test
2. WHEN a data transformation function exists THEN the system SHALL have an invariant property test
3. WHEN a search/filter function exists THEN the system SHALL have a metamorphic property test

### Requirement 9: Remove Legacy Compatibility Code

**User Story:** As a maintainer, I want to remove code that exists only for backward compatibility with removed features, so that the codebase is cleaner.

#### Acceptance Criteria

1. WHEN legacy mode strings are referenced THEN the system SHALL remove support for deprecated modes
2. WHEN legacy API endpoints exist THEN the system SHALL either remove them or document their deprecation timeline
3. WHEN legacy serialization formats are referenced THEN the system SHALL remove fallback handling for them

### Requirement 10: Standardize Error Handling Patterns

**User Story:** As a developer, I want consistent error handling patterns across the codebase, so that errors are handled predictably.

#### Acceptance Criteria

1. WHEN a custom exception class is needed THEN the system SHALL inherit from a base exception class defined in `core.py`
2. WHEN an operation can fail THEN the system SHALL use specific exception types rather than generic Exception
3. WHEN errors are logged THEN the system SHALL include structured context (operation, parameters, duration)
