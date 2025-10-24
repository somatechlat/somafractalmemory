# Upgrade Features Documentation

## OPA Policy Enforcement
- All API endpoints now enforce dynamic OPA policies via REST calls.
- Denied requests return 403 with audit logging.
- OPA endpoint and policy path are configurable in settings.

## JWT Authentication
- Static bearer token replaced with JWT validation.
- Configurable issuer, audience, secret/public key.
- Strict error handling for expired/invalid tokens.

## Retry/Backoff
- Redis and Etcd adapters use tenacity for exponential backoff and retries.
- Circuit breaker/fallback logic for persistent failures.

## Tracing
- All storage adapters instrumented with OpenTelemetry spans.
- Trace context propagated from API through backend calls.

## Backup and Restore
- Automated scheduled backup jobs and manual restore endpoints.
- Supports local and cloud/object storage (S3).
- Status reporting and error handling.

## Metrics Coverage
- Prometheus metrics for API, Redis, Etcd, and seeder operations, errors, retries, and OPA denials.
- Metrics exposed on `/metrics` endpoint and seeder port 8001.

## Config and Secrets
- Centralized config with validation and runtime reload.
- Vault/Kubernetes secrets integration supported.

## Test Coverage and CI
- New tests for all upgraded features.
- CI pipeline runs tests, lint, type-check, and security scans.

---
See `docs/technical-manual/backup-and-recovery.md` for backup details.
See `tests/test_upgrade_features.py` for upgrade feature tests.
