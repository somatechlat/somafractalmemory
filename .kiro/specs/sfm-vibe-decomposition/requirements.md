# Requirements Document - SomaFractalMemory VIBE Decomposition

## Introduction

This specification addresses critical VIBE Coding Rules violations in the SomaFractalMemory repository. The primary violations are monolithic files exceeding the 500-line limit, which violate VIBE Rule 2 (CHECK FIRST, CODE SECOND) and make code review and maintenance difficult.

## Glossary

- **SFM**: SomaFractalMemory - the enterprise-grade agentic memory system
- **VIBE Rules**: The project's coding standards requiring no placeholders, real implementations, and manageable file sizes
- **Decomposition**: Breaking large files into smaller, focused modules

## Requirements

### Requirement 1

**User Story:** As a developer, I want core.py to be under 500 lines, so that I can review and maintain the code effectively.

#### Acceptance Criteria

1. WHEN the decomposition is complete THEN the system SHALL have core.py under 500 lines
2. WHEN methods are extracted THEN the system SHALL maintain all existing functionality
3. WHEN modules are created THEN the system SHALL use proper imports without circular dependencies
4. WHEN the refactoring is done THEN the system SHALL pass all existing tests

### Requirement 2

**User Story:** As a developer, I want http_api.py to be under 500 lines, so that API routes are organized and maintainable.

#### Acceptance Criteria

1. WHEN the decomposition is complete THEN the system SHALL have http_api.py under 500 lines
2. WHEN routes are extracted THEN the system SHALL maintain all API endpoints
3. WHEN Pydantic models are extracted THEN the system SHALL maintain request/response validation
4. WHEN the refactoring is done THEN the system SHALL pass all API tests

### Requirement 3

**User Story:** As a developer, I want storage.py to be under 500 lines, so that storage implementations are focused and testable.

#### Acceptance Criteria

1. WHEN the decomposition is complete THEN the system SHALL have storage.py under 500 lines
2. WHEN PostgresKeyValueStore is extracted THEN the system SHALL maintain KV operations
3. WHEN MilvusVectorStore is extracted THEN the system SHALL maintain vector operations
4. WHEN the refactoring is done THEN the system SHALL pass all storage tests

### Requirement 4

**User Story:** As a developer, I want postgres_graph.py to be under 500 lines, so that graph operations are maintainable.

#### Acceptance Criteria

1. WHEN the decomposition is complete THEN the system SHALL have postgres_graph.py under 500 lines
2. WHEN helper functions are extracted THEN the system SHALL maintain graph functionality
3. WHEN the refactoring is done THEN the system SHALL pass all graph tests
