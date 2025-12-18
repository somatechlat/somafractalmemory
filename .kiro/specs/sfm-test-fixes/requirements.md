# Requirements Document - SomaFractalMemory Test Fixes

## Introduction

This document specifies the requirements for fixing the remaining test failures in SomaFractalMemory after the VIBE decomposition work. The failures are related to namespace isolation in memory statistics and Postgres connection pool exhaustion during concurrent tenant tests.

## Glossary

- **Namespace**: A logical partition for memory data, typically corresponding to a tenant or application context
- **Milvus Collection**: A vector database collection in Milvus, named after the namespace
- **KV Store**: Key-Value store (PostgreSQL + Redis hybrid) for memory metadata
- **Vector Store**: Milvus-based store for embedding vectors
- **Connection Pool**: A pool of reusable database connections managed by SQLAlchemy

## Requirements

### Requirement 1: Namespace-Scoped Memory Statistics

**User Story:** As a developer, I want memory_stats() to return counts only for the current namespace, so that statistics accurately reflect the isolated memory space.

#### Acceptance Criteria

1. WHEN memory_stats() is called THEN the system SHALL return total_memories count only for keys matching the current namespace pattern
2. WHEN memory_stats() is called THEN the system SHALL return vector_count only from the namespace's Milvus collection
3. WHEN memory_stats() is called on a fresh namespace THEN the system SHALL return zero for total_memories and vector_count
4. WHEN memory_stats() is called THEN the system SHALL NOT aggregate counts from other namespaces or collections

### Requirement 2: Connection Pool Resilience

**User Story:** As a system operator, I want concurrent tenant operations to not exhaust the database connection pool, so that the system remains stable under load.

#### Acceptance Criteria

1. WHEN multiple tenants are created concurrently THEN the system SHALL reuse connections from the pool
2. WHEN the connection pool is near capacity THEN the system SHALL queue requests rather than fail
3. WHEN running concurrent tenant tests THEN the system SHALL complete without connection exhaustion errors
4. IF connection pool exhaustion occurs THEN the system SHALL log a warning and retry with backoff

### Requirement 3: Test Infrastructure Cleanup

**User Story:** As a developer, I want test infrastructure to be properly cleaned between test runs, so that tests are isolated and reproducible.

#### Acceptance Criteria

1. WHEN a test creates a namespace THEN the system SHALL use a unique identifier to avoid collisions
2. WHEN test_memory_stats_counts runs THEN the system SHALL start with zero memories in the test namespace
3. WHEN concurrent tenant tests run THEN the system SHALL properly isolate each tenant's data
