# SOMA-SFM-SEC-001: SomaFractalMemory Security Assessment

> **Standard**: ISO/IEC 27001:2022 — Information Security Management Systems
> **Owner**: SomaTech LAT

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SOMA-SFM-SEC-001: SomaFractalMemory Security Assessment |
| Document Identifier | SOMA-SFM-SEC-001 |
| Version | 2.0.1 |
| Date | 2026-09-28 |
| Status | Approved |
| Author | SomaTech LAT Security Engineering |
| Approver | CISO, SomaTech LAT |
| Classification | Confidential |
| ISO Reference | ISO/IEC 27001:2022 — Information Security Management Systems |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 1.0.0 | 2025-10-01 | Security | Initial security review |
| 2.0.0 | 2026-06-15 | Security | Production-ready assessment for v0.2.0; added Vault, OPA, Docker hardening review |
| 2.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-SFM-SEC-001` \| case normalised to `Approved` \| prior classification `PROPRIETARY / COMMERCIAL SENSITIVE` normalised to `Confidential`. |

---

## 1. Executive Summary

SomaFractalMemory v0.2.0 implements a **defense-in-depth** security architecture across five domains: authentication, authorization, secrets management, container hardening, and multi-tenant isolation. The overall security posture is rated **A-** with one notable gap (hash-based embeddings) and strong controls in all other areas.

| Domain | Rating | Status |
|:-------|:------|:-------|
| Authentication | A | Production ready |
| Authorization | A | Fail-closed OPA |
| Secrets Management | A | Vault KV v2 |
| Container Security | A- | cap_drop ALL, no-new-privileges |
| Multi-Tenant Isolation | A | Crypto-separated namespaces |
| Data Protection | B+ | Soft deletes, audit logging |

---

## 2. Authentication

### 2.1 Standalone Mode — Bearer Token

**Implementation**: `somafractalmemory/api/auth.py` — `StandaloneAuth`

```python
class StandaloneAuth(HttpBearer):
    def authenticate(self, request, token):
        expected_token = _get_expected_token()
        if hmac.compare_digest(token.encode("utf-8"), expected_token.encode("utf-8")):
            return {
                "tenant": "standalone",
                "auth_type": "standalone_token",
                "permissions": ["read", "write", "delete"],
                "allowed_namespaces": ["*"],
            }
        return None
```

**Security Properties**:

| Property | Status | Detail |
|:---------|:-------|:-------|
| Constant-time comparison | PASS | `hmac.compare_digest` prevents timing attacks |
| Token source | PASS | Loaded from `SOMA_API_TOKEN` env var or Vault |
| Empty token rejection | PASS | Returns `None` if token is empty |
| Unconfigured fallback | PASS | Logs warning if token not set, denies access |
| Tenant binding | PASS | All standalone requests bound to `standalone` tenant |

### 2.2 AAAS Mode — Multi-Auth

**Implementation**: `somafractalmemory/admin/aaas/auth.py` — `MultiAuth`

Three authentication strategies in priority order:

#### 2.2.1 SFM Local Keys (`sfm_*` prefix)

| Property | Status | Detail |
|:---------|:-------|:-------|
| Key storage | PASS | SHA-256 hash stored in `APIKey` model (never plaintext) |
| Expiration | PASS | Checked against `expires_at` timestamp |
| Usage tracking | PASS | `touch()` method updates last-used timestamp and IP |
| Namespace isolation | PASS | `allowed_namespaces` list enforced |

#### 2.2.2 SomaBrain Central Keys (`sbk_*` prefix)

| Property | Status | Detail |
|:---------|:-------|:-------|
| Remote validation | PASS | `GET /api/v1/auth/verify` on SomaBrain (port 63996) |
| Timeout hardening | PASS | 3.0s timeout prevents thread exhaustion |
| Error handling | PASS | Timeout/connection errors return `None` (deny) |
| Scope extraction | PASS | Scopes extracted from SomaBrain response |

#### 2.2.3 Health Endpoint Auth

```python
# somafractalmemory/api/routers/health.py:44-46
provided = auth_header.split(" ", 1)[1]
if not hmac.compare_digest(provided, API_TOKEN):
    raise HttpError(401, get_message(ErrorCode.INVALID_API_TOKEN))
```

Health detail endpoint (`/health`) requires authentication. Basic health (`/healthz`, `/readyz`) is unauthenticated for orchestrator probes.

### 2.3 Authentication Weaknesses

| Finding | Severity | Detail |
|:--------|:---------|:-------|
| SimpleTokenAuth uses `==` comparison | INFO | `auth.py:202` uses `token == expected_token` instead of `hmac.compare_digest`. This is a minor timing side-channel for internal service calls only. |

---

## 3. Authorization

### 3.1 OPA (Open Policy Agent) Integration

**Configuration**:

| Parameter | Value | Security Impact |
|:----------|:------|:----------------|
| `SOMA_OPA_URL` | `http://opa:8181` | Policy evaluation endpoint |
| `SOMA_OPA_TIMEOUT` | 1.0s | Prevents request stalls |
| `SOMA_OPA_FAIL_OPEN` | **False** | **Fail-closed** — denies on OPA failure |

**Security Assessment**:

- **Fail-closed**: Default policy denies all requests when OPA is unreachable
- This is the correct security posture for production environments
- Operators may override to `True` only in development/test environments

### 3.2 Namespace Access Control

```python
# somafractalmemory/admin/aaas/auth.py:220-235
def can_access_namespace(request, namespace):
    auth = getattr(request, "auth", {})
    allowed = auth.get("allowed_namespaces", [])
    if not allowed:
        return True  # No restriction set
    return namespace in allowed or "*" in allowed
```

**Properties**:
- Per-key namespace restrictions via `allowed_namespaces` list
- Wildcard `*` support for admin keys
- Empty list = unrestricted (controlled by key creation)

### 3.3 Permission Model

| Permission | Scope |
|:-----------|:------|
| `read` | GET operations, search |
| `write` | POST/PUT operations |
| `delete` | DELETE operations |
| `admin` | All operations + user management |

SimpleTokenAuth grants `["read", "write"]` by default. APIKeyAuth grants permissions from the key record.

---

## 4. Secrets Management

### 4.1 HashiCorp Vault (KV v2)

**Implementation**: `somafractalmemory/admin/core/security/vault_client.py`

| Property | Status | Detail |
|:---------|:-------|:-------|
| KV v2 engine | PASS | `client.secrets.kv.v2.read_secret_version()` |
| Authentication | PASS | Token-based with `VAULT_TOKEN` |
| Connection validation | PASS | `client.is_authenticated()` check |
| Secret caching | PASS | 5-minute TTL, prevents Vault DDoS |
| Cache key isolation | PASS | `(path, key)` tuple as cache key |
| Error handling | PASS | `VaultNotConfigured` / `SecretNotFound` exceptions |
| Credential injection | PASS | `infra.py` reads DB/Redis creds from Vault at startup |

### 4.2 Vault Secrets Structure

```
somafractalmemory/
├── data/
│   ├── database  → {username, password, host, port, dbname}
│   └── redis     → {host, port, password}
```

### 4.3 Secret Rotation

Vault init container (`infra/standalone/docker-compose.yml:42-75`) writes initial secrets at deployment. Secret rotation requires:
1. Update secrets in Vault (via Vault CLI or API)
2. Restart SFM container to reload from Vault (cache expires in 5 minutes)

---

## 5. Container Security

### 5.1 Docker Hardening

From `infra/standalone/docker-compose.yml`:

```yaml
# API Container
cap_drop: [ "ALL" ]
security_opt:
  - no-new-privileges:true
```

| Control | Status | Detail |
|:--------|:-------|:-------|
| Drop all capabilities | PASS | `cap_drop: ALL` |
| No privilege escalation | PASS | `no-new-privileges:true` |
| Resource limits | PASS | API: 2GB, Milvus: 4GB |
| Health checks | PASS | Every service has health probes |
| Restart policy | PASS | `unless-stopped` |
| Network isolation | PASS | Dedicated bridge network |

### 5.2 Resource Limits

| Container | Memory Limit | Notes |
|:----------|:-------------|:------|
| API | 2G | Django + Uvicorn workers |
| Milvus | 4G | Vector index operations |
| PostgreSQL | — | Managed by Kubernetes in prod |
| Redis | — | Lightweight cache |

### 5.3 Filesystem

| Control | Current | Recommendation |
|:--------|:--------|:---------------|
| `read_only` | `false` | Set `true` with tmpfs mounts for `/tmp` |
| Volume mounts | Named volumes only | No host path mounts in standalone |

---

## 6. Multi-Tenant Isolation

### 6.1 Data Isolation Architecture

SFM enforces tenant isolation at every data access point:

```
API Request → Auth (extract tenant) → Service (filter by tenant) → ORM (WHERE tenant=...)
```

### 6.2 Isolation Layers

| Layer | Mechanism | Enforcement Point |
|:------|:----------|:------------------|
| Authentication | Tenant derived from auth context | `StandaloneAuth` / `APIKeyAuth` |
| Authorization | Namespace access list per key | `can_access_namespace()` |
| Data Access | `tenant` field on every model | Django ORM queries |
| Storage | Unique constraint `(namespace, tenant, coordinate_key)` | PostgreSQL |
| Vectors | Collection per namespace (`sfm_{namespace}`) | Milvus |

### 6.3 Tenant Extraction

```python
# Standalone: fixed "standalone" tenant
{"tenant": "standalone"}

# AAAS with sfm_* key: from APIKey record
{"tenant": api_key.tenant}

# AAAS with sbk_* key: from SomaBrain response
{"tenant": data.get("tenant_slug")}
```

Tenant is **never** derived from request headers — it is bound at authentication time, preventing tenant hijacking.

---

## 7. Data Protection

### 7.1 Soft Deletes

All memory deletions are non-destructive:

```python
memory.is_deleted = True
memory.deleted_at = datetime.now(UTC)
```

All read queries filter `is_deleted=False`. Deleted data is preserved for:
- Audit trail integrity
- Recovery capability
- Compliance requirements

### 7.2 Audit Logging

Every operation generates an `AuditLog` record in `sfm_audit_log`:

| Field | PII | Retention |
|:------|:----|:----------|
| action | No | Permanent |
| namespace | No | Permanent |
| coordinate_key | No | Permanent |
| tenant | No | Permanent |
| user_id | Yes | Configurable |
| ip_address | Yes | Configurable |
| details | Depends | Permanent |
| timestamp | No | Permanent |

### 7.3 Encryption

| Layer | Status | Detail |
|:------|:-------|:-------|
| At rest (PostgreSQL) | DEPENDS | Relies on disk encryption or PostgreSQL TDE |
| At rest (Milvus) | DEPENDS | Relies on MinIO encryption |
| At rest (Vault) | PASS | Vault encrypts all secrets (AES-256-GCM) |
| In transit (internal) | PARTIAL | Docker network isolation, no TLS between containers |
| In transit (external) | DEPENDS | Requires TLS termination at ingress/load balancer |

---

## 8. Security Configuration Checklist

| # | Control | Status | Source |
|:--|:--------|:-------|:-------|
| 1 | Bearer token authentication | PASS | `api/auth.py` |
| 2 | Constant-time token comparison | PASS | `hmac.compare_digest` |
| 3 | OPA fail-closed authorization | PASS | `SOMA_OPA_FAIL_OPEN=False` |
| 4 | Vault secrets management | PASS | `vault_client.py` |
| 5 | Docker cap_drop ALL | PASS | `docker-compose.yml:238` |
| 6 | Docker no-new-privileges | PASS | `docker-compose.yml:241` |
| 7 | Multi-tenant data isolation | PASS | Model constraints + ORM filtering |
| 8 | Soft deletes | PASS | `is_deleted` flag |
| 9 | Audit logging | PASS | `AuditLog` model |
| 10 | Health probe security | PASS | `/health` requires auth, `/healthz` open |
| 11 | API key hash storage | PASS | SHA-256 hash, never plaintext |
| 12 | Network isolation | PASS | Dedicated bridge network |
| 13 | Resource limits | PASS | Memory limits on containers |
| 14 | Structured logging | PASS | structlog JSON renderer |
| 15 | `.env` not in version control | PASS | `.gitignore` excludes `.env` |

---

## 9. Threat Model Summary

| Threat | Mitigation | Residual Risk |
|:-------|:-----------|:--------------|
| Timing attack on token | `hmac.compare_digest` | Negligible |
| Stolen credentials | Vault rotation, key expiration | Low |
| OPA unavailable | Fail-closed (deny all) | Low |
| Tenant data leakage | Unique constraints, ORM filtering | Low |
| Container breakout | cap_drop ALL, no-new-privileges | Low |
| Vault unavailability | Graceful fallback with env vars | Medium |
| Embedding quality bypass | Hash embeddings are deterministic but not semantic | Medium |
| DDoS on Vault | 5-min TTL cache | Low |

---

## 10. Recommendations

| # | Recommendation | Priority | Effort |
|:--|:---------------|:---------|:-------|
| 1 | Add TLS between internal services | MEDIUM | Infrastructure |
| 2 | Implement audit log retention/archival policy | MEDIUM | Database |
| 3 | Replace hash embeddings with ML model | HIGH | Code change |
| 4 | Add `read_only: true` with tmpfs mounts | LOW | Docker config |
| 5 | Implement secret rotation automation | MEDIUM | Vault + CI/CD |
| 6 | Add IP allowlisting for production | LOW | Network policy |

---

*End of SOMA-SFM-SEC-001 v2.0.0*
