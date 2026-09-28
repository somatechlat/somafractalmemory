# Production Readiness Checklist

## Document Control

| Field | Value |
|---|---|
| Document Title | Production Readiness Checklist |
| Document Identifier | SOMA-SFM-GUIDE-PROD-001 |
| Version | 1.0.0 |
| Date | 2026-09-28 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |


## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. Brought under the house ISO document-control contract. |


> Last updated: 2026-05-18

## Overview

This document tracks the production readiness of SomaFractalMemory.

## Checklist

### Infrastructure
- [ ] PostgreSQL 15+ deployed with SSL/TLS
- [ ] Redis 7+ deployed with persistence enabled
- [ ] Milvus 2.3+ deployed and initialized
- [ ] HashiCorp Vault configured for secret injection (production)
- [ ] Open Policy Agent (OPA) configured (optional but recommended)

### Security
- [ ] `SOMA_API_TOKEN` set to a strong random value
- [ ] `SOMA_SECRET_KEY` set to a strong random value
- [ ] `SOMA_ALLOWED_HOSTS` restricted to actual hostnames
- [ ] JWT secrets rotated and stored in Vault (if using JWT mode)
- [ ] Network policies restrict internal service access

### Configuration
- [ ] `SOMA_API_PORT` set (default: 10101)
- [ ] `SOMA_POSTGRES_URL` or individual `POSTGRES_*` vars configured
- [ ] `SOMA_MILVUS_HOST` and `SOMA_MILVUS_PORT` configured
- [ ] `REDIS_URL` or individual `REDIS_*` vars configured
- [ ] `SOMA_OPA_URL` configured (if using OPA)
- [ ] `LOG_LEVEL` set to `INFO` or `WARNING` in production

### Health & Monitoring
- [ ] `/healthz` endpoint responding (liveness probe)
- [ ] `/readyz` endpoint responding (readiness probe)
 [ ] `/metrics` endpoint scraped by Prometheus
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

## Known Limitations

- Project version (`0.2.0`) and API OpenAPI version (`2.0.0`) are intentionally decoupled. See README for details.

## References

- [Deployment Guide](deployment.md)
- [Architecture](architecture.md)
- [OPS Manual](OPS_MANUAL.md)
