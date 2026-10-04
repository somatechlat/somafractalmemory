# Production Readiness Checklist

## Document Control

| Field | Value |
|---|---|
| Document Title | Production Readiness Checklist |
| Document Identifier | SOMA-SFM-GUIDE-PROD-001 |
| Version | 1.1.0 |
| Date | 2026-10-03 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-03 |


## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. Brought under the house ISO document-control contract. |
| 1.1.0 | 2026-10-03 | SomaTech Engineering | Truth pass against the code. Removed JWT mode, `SOMA_API_PORT`, `SOMA_POSTGRES_URL`, `SOMA_OPA_URL` and the OPA checklist item — those knobs were deleted because nothing reads them (`settings/infra.py`). Replaced with the knobs that exist (`TUNABLES` in `settings/model.py`). |


> Last updated: 2026-10-03

## Overview

This document tracks the production readiness of SomaFractalMemory.

A checked item must be verifiable against this tree. Items for features that do
not exist are **not** listed: a config knob with no reader is a lie. The
deleted knobs and why they were deleted are recorded in
`settings/infra.py` and in `docs/iso/SOMA-SFM-ARCH-001` Appendix A.

## Checklist

### Infrastructure
- [ ] PostgreSQL 15+ deployed with SSL/TLS
- [ ] Redis 7+ deployed with persistence enabled
- [ ] Milvus 2.3+ deployed and initialized
- [ ] HashiCorp Vault configured for secret injection (production)
- [ ] Vault is reachable at startup — `_credential` **raises** on Vault failure; there is no ENV fallback

### Security
- [ ] `SOMA_API_TOKEN` set to a strong random value (the only credential in standalone mode)
- [ ] `SOMA_SECRET_KEY` set to a strong random value
- [ ] `SOMA_ALLOWED_HOSTS` restricted to actual hostnames
- [ ] Network policies restrict internal service access
- [ ] Operators understand the single shared bearer token: rotation is a coordinated restart

### Configuration
- [ ] `SOMA_DB_HOST`, `SOMA_DB_PORT`, `SOMA_DB_NAME` set (topology)
- [ ] `SOMA_DB_USER` / `SOMA_DB_PASSWORD` sourced from Vault (`somafractalmemory/database`)
- [ ] `SOMA_MILVUS_HOST` and `SOMA_MILVUS_PORT` configured
- [ ] `SOMA_REDIS_HOST` / `SOMA_REDIS_PORT` configured (optional — absent means no Redis)
- [ ] `SOMA_VECTOR_DIM` matches the agent seam (`MEM_EMBED_DIM`); default **768**
- [ ] `SOMA_LOG_LEVEL` set to `INFO` or `WARNING` in production

### Health & Monitoring
- [ ] `/healthz` endpoint responding (liveness probe)
- [ ] `/readyz` endpoint responding (readiness probe)
- [ ] `/metrics` endpoint scraped by Prometheus
- [ ] OpenTelemetry collector configured

### Backup & Disaster Recovery
- [ ] PostgreSQL backup strategy in place (`pg_dump` or WAL archiving)
- [ ] Redis persistence configured (AOF or RDB)
- [ ] Milvus backup strategy documented
- [ ] Recovery procedures tested quarterly

### Compliance
- [ ] No SQLAlchemy imports (100% Django ORM)
- [ ] No FastAPI imports (100% Django Ninja)
- [ ] Audit logging enabled
- [ ] GDPR/HIPAA data handling procedures documented

## Not in this product (do not configure)

| Absent capability | Evidence |
|:------------------|:---------|
| JWT / per-identity auth | `SOMA_JWT_*` deleted; auth is the `SOMA_API_TOKEN` bearer |
| OPA authorization | No OPA client. `SOMA_OPA_*` deleted. The composed OPA container has no consumer. |
| Rate limiting | No middleware. `SOMA_RATE_LIMIT_*` deleted. |
| CORS policy | No middleware. `SOMA_CORS_ORIGINS` deleted. |
| Request body cap | No middleware. `SOMA_MAX_REQUEST_BODY_MB` deleted. |
| Circuit breaker | No breaker in this tree. `SOMA_CIRCUIT_*` deleted. |
| Batch upsert | `store()` writes one row per call. |
| Decay / pruning | No decay scorer, no prune command. |
| Hybrid score fusion | Ranking is vector score + hash penalty + ORM fallback. |

## Known Limitations

- Project version (`0.2.0`) and API OpenAPI version (`2.0.0`) are intentionally decoupled. See README for details.
- AAAS multi-tenant auth is **not deployed** (see `SOMA-SFM-ARCH-001` §2.2).

## References

- [Deployment Guide](deployment.md)
- [Architecture](architecture.md)
- [OPS Manual](OPS_MANUAL.md)
