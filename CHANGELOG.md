# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Fix: `eventing/producer.py` now emits ISO8601 UTC timestamps to conform with `schemas/memory.event.json`.
- Fix: `workers/kv_writer.py` normalises incoming `timestamp` values (accepts numeric epoch and ISO strings) to preserve compatibility.
- Docs: Added `docs/PRODUCTION_READINESS.md` and linked it from canonical docs and README.
- Docs: Updated architecture, monitoring, port strategy, and runbooks to reflect unified port assignments (API 10101 and backing stores per current Milvus deployment).

### Changed
- **Standardized Docker Images**: Replaced all third-party Docker images (e.g., `bitnami/kafka`, `confluentinc/cp-kafka`) with their official open-source counterparts (`apache/kafka`, `postgres`, `redis`). This applies to both Docker Compose and Kubernetes Helm charts.
- **Simplified Test Suite**: Drastically reduced the test suite from 37+ complex tests to 8 core, efficient end-to-end tests. Test execution time improved from over 5 minutes to under 8 seconds.
- **Corrected Kubernetes Deployment**: Fixed multiple errors in the Helm chart templates, allowing for a successful and repeatable deployment to a local `kind` cluster.
- **Resolved Port Conflicts**: Kubernetes services now expose the same port assignments as Docker Compose (API `10101`, backing stores `40021-40023`), eliminating dual-range drift.

### Added
- **Comprehensive Documentation Structure**: Implemented the full four-manual documentation system (`User`, `Technical`, `Development`, `Onboarding`) as per the project's `Documentation Guide Template`.
- **New Documentation Content**: Created all missing documentation files required by the template, populated with accurate, code-derived information.
- **Kubernetes Local Development Guide**: Added a new section to the `DEVELOPER_MANUAL.md` with step-by-step instructions for deploying and testing on a local `kind` cluster.
- **Compliance Audit**: Added a `COMPLIANCE_AUDIT.md` file to track and verify project cleanup and documentation compliance.

### Removed
- **Redundant and Inefficient Tests**: Deleted 29+ test files that were slow, complex, or redundant.
- **Duplicate Documentation**: Removed duplicate and conflicting style guides.
- **Misleading Analysis Files**: Deleted temporary analysis and report files.
- **Legacy Configuration**: Deleted the unused `test_config.yaml` file.
- **Obsolete Makefile Targets**: Removed the non-functional `docs-build` and `docs-serve` commands from the `Makefile`.
- **Deprecated Code**: Removed the `recall_with_scores` function from `core.py`, which was marked as deprecated.
- **Unused Event Schema**: Deleted the `schemas/` directory, which was only used by the legacy Kafka eventing system.
- **Orphaned Artifacts**: Removed empty directories (`.venv-test/include`, `docs/onboarding-manual/checklists`) left over from previous refactoring.
