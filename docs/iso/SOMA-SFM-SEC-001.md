# SOMA-SFM-SEC-001: SomaFractalMemory Security Assessment

> **Standard**: ISO/IEC 27001:2022 — Information Security Management Systems
> **Owner**: SomaTech LAT

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SOMA-SFM-SEC-001: SomaFractalMemory Security Assessment |
| Document Identifier | SOMA-SFM-SEC-001 |
| Version | 2.1.0 |
| Date | 2026-10-03 |
| Status | Draft |
| Author | SomaTech LAT Security Engineering |
| Approver | — |
| Classification | Confidential |
| ISO Reference | ISO/IEC 27001:2022 — Information Security Management Systems |
| Next Review | 2027-01-03 |
| Related | `somafractalmemory/api/auth.py`, `somafractalmemory/settings/infra.py` |

## Revision History

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 1.0.0 | 2025-10-01 | Security | Initial security review |
| 2.0.0 | 2026-06-15 | Security | Production-ready assessment for v0.2.0; added Vault, OPA, Docker hardening review |
| 2.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-SFM-SEC-001` \| case normalised to `Approved` \| prior classification `PROPRIETARY / COMMERCIAL SENSITIVE` normalised to `Confidential`. |
| 2.1.0 | 2026-10-03 | SomaTech Engineering | Truth pass against the code. Removed the fail-closed OPA claim: there is no OPA client in this tree (`SOMA_OPA_*` knobs deleted with the absent gate; `settings/infra.py:69-71`). Removed AAAS MultiAuth / `APIKeyAuth` / `sbk_*` claims: `admin/aaas/auth.py` does not exist and `APIKey` was dropped in migration `0006`. Authorization is the `SOMA_API_TOKEN` bearer plus fail-closed namespace/tenant checks. Status returned to Draft (meaning change per SOMA-SFM-DOCS-001 §3.4). |

---

## 1. Executive Summary

SomaFractalMemory v0.2.0 implements a **defense-in-depth** security architecture across five domains: authentication, authorization, secrets management, container hardening, and multi-tenant isolation. The overall security posture is rated **A-** with one notable gap (hash-based embeddings) and strong controls in all other areas.

| Domain | Rating | Status |
|:-------|:------|:-------|
| Authentication | A | Bearer token (`SOMA_API_TOKEN`), constant-time compare |
| Authorization | B | Bearer-bound namespace/tenant checks. **No OPA client** — the OPA container is composed but nothing calls it. |
| Secrets Management | A | Vault KV v2, fail-closed on Vault error |
| Container Security | A- | cap_drop ALL, no-new-privileges |
| Multi-Tenant Isolation | A | Namespace isolation + ORM `tenant` filtering |
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

**Not implemented.** Earlier revisions documented `MultiAuth` / `APIKeyAuth` in
`SomaFractalMemory/admin/aaas/auth.py`. That module does not exist. The
`APIKey` and `UsageRecord` models were dropped in migration
`0006_drop_apikey_usagerecord.py`. `api/auth.py:1-9` states the shipped
surface explicitly: "Authentication for STANDALONE mode only… No API key
management, no SomaBrain integration."

There is no `sfm_*` key path, no `sbk_*` SomaBrain validation path, and no
per-key namespace allow-list in this tree.

### 2.3 Health Endpoint Auth

```python
# somafractalmemory/api/routers/health.py
provided = auth_header.split(" ", 1)[1]
if not hmac.compare_digest(provided, API_TOKEN):
    raise HttpError(401, get_message(ErrorCode.INVALID_API_TOKEN))
```

Health detail endpoint (`/health`) requires authentication. Basic health
(`/healthz`, `/readyz`) is unauthenticated for orchestrator probes.

### 2.4 Authentication Weaknesses

| Finding | Severity | Detail |
|:--------|:---------|:-------|
| Single shared bearer token | INFO | Standalone mode has one `SOMA_API_TOKEN` for every caller. There is no per-identity credential in this tree. Rotating the token is a coordinated restart. |
| No rate limiting | INFO | No rate-limit middleware exists (`settings/django_core.py:181-185`). `SOMA_RATE_LIMIT_*` knobs were deleted with the absent gate. Brute-force resistance is the constant-time compare plus network boundary only. |
| No request body cap | INFO | No body-size middleware. `SOMA_MAX_REQUEST_BODY_MB` was deleted with the absent reader. |

---

## 3. Authorization

### 3.1 OPA (Open Policy Agent)

**There is no OPA client in this tree.** This is the single largest correction
in this revision.

Earlier revisions claimed "Fail-closed OPA" with `SOMA_OPA_URL` /
`SOMA_OPA_TIMEOUT` / `SOMA_OPA_FAIL_OPEN` governing request authorization.
None of that is true:

| Claim | Code truth |
|:------|:-----------|
| OPA evaluates every request | No OPA client exists. No module opens an HTTP connection to OPA. |
| `SOMA_OPA_FAIL_OPEN=False` denies on OPA failure | The `SOMA_OPA_*` knobs were deleted. Nothing reads them (`settings/infra.py:69-71`). |
| Fail-closed OPA is the authorization gate | Authorization is the `SOMA_API_TOKEN` bearer via `StandaloneAuth`, plus fail-closed namespace/tenant checks in `api/utils.py` and `api/auth.py`. |

An OPA container **is** composed in `infra/standalone/docker-compose.yml:98-110`
and `SOMA_OPA_URL` is set as an environment variable on the API container
(`docker-compose.yml:232`). That is infrastructure without a consumer: a
config knob with no reader is a lie. The knobs were deleted; the container
remains and is not a security control until a client exists.

**Fail-closed behaviour that does exist** (and is the real authorization
posture):

| Gate | Location | Behaviour |
|:-----|:---------|:----------|
| Bearer token | `api/auth.py` `StandaloneAuth` | Unconfigured token rejects every caller |
| Token compare | `api/auth.py` | `hmac.compare_digest`, constant-time |
| Namespace allow-list | `api/auth.py:75-` `can_access_namespace` | **Empty allow-list grants nothing** (fail-closed, R-05 / F-07 / T-5) |
| Tenant resolution | `api/utils.py` | Missing tenant denies; never remapped to default |
| Vault credentials | `settings/django_core._credential` | Vault error raises; never falls through to ENV |
| Vector dim | `settings/infra._read_vector_dim` | Dim is named or refused; never guessed |

### 3.2 Namespace Access Control

```python
# somafractalmemory/api/auth.py:75-
def can_access_namespace(request: HttpRequest, namespace: str) -> bool:
    """Fail-closed (R-05 / F-07, T-5): an empty allow-list grants nothing."""
```

Standalone auth sets `allowed_namespaces = ["*"]` at authentication time, so
the happy path is unrestricted. A caller whose auth context carries an empty
list is denied. This is the opposite of the pre-2.1.0 text, which claimed an
empty list meant unrestricted.

### 3.3 Permission Model

| Permission | Scope |
|:-----------|:------|
| `read` | GET operations, search |
| `write` | POST/PUT operations |
| `delete` | DELETE operations |

`StandaloneAuth` grants `["read", "write", "delete"]` to every holder of the
token. There is no per-identity permission record in this tree.

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
| Authentication | Tenant derived from auth context | `StandaloneAuth` |
| Authorization | Namespace access list | `can_access_namespace()` (`api/auth.py`) |
| Data Access | `tenant` field on every model | Django ORM queries |
| Storage | Unique constraint `(namespace, tenant, coordinate_key)` | PostgreSQL |
| Vectors | Collection per namespace (`sfm_{namespace}`) | Milvus |

### 6.3 Tenant Extraction

```python
# Standalone: fixed "standalone" tenant
{"tenant": "standalone"}
```

Tenant is **never** derived from request headers — it is bound at authentication
time, preventing tenant hijacking. There is no AAAS path that extracts a tenant
from an `APIKey` record or a SomaBrain response (see §2.2).

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
| 3 | OPA authorization | **ABSENT** | No OPA client in this tree. `SOMA_OPA_*` knobs deleted (`settings/infra.py:69-71`). The composed OPA container is not a control. |
| 4 | Vault secrets management | PASS | `vault_client.py`; Vault failure raises (no ENV fallback) |
| 5 | Docker cap_drop ALL | PASS | `docker-compose.yml` |
| 6 | Docker no-new-privileges | PASS | `docker-compose.yml` |
| 7 | Multi-tenant data isolation | PASS | Model constraints + ORM filtering |
| 8 | Soft deletes | PASS | `is_deleted` flag |
| 9 | Audit logging | PASS | `AuditLog` model |
| 10 | Health probe security | PASS | `/health` requires auth, `/healthz` open |
| 11 | API key hash storage | **ABSENT** | No `APIKey` model (dropped in migration `0006`). No per-key credentials. |
| 12 | Network isolation | PASS | Dedicated bridge network |
| 13 | Resource limits | PASS | Memory limits on containers |
| 14 | Structured logging | PASS | structlog JSON renderer |
| 15 | `.env` not in version control | PASS | `.gitignore` excludes `.env` |
| 16 | Rate limiting | **ABSENT** | No rate-limit middleware. `SOMA_RATE_LIMIT_*` deleted. |
| 17 | Request body cap | **ABSENT** | No body-size middleware. `SOMA_MAX_REQUEST_BODY_MB` deleted. |
| 18 | CORS restriction | **ABSENT** | No CORS middleware (`settings/django_core.py:181-185`). `SOMA_CORS_ORIGINS` deleted. |
| 19 | Circuit breaker | **ABSENT** | No breaker in this tree. `SOMA_CIRCUIT_*` deleted. |
| 20 | JWT / per-identity auth | **ABSENT** | Auth is the shared `SOMA_API_TOKEN` bearer. `SOMA_JWT_*` deleted. |

---

## 9. Threat Model Summary

| Threat | Mitigation | Residual Risk |
|:-------|:-----------|:--------------|
| Timing attack on token | `hmac.compare_digest` | Negligible |
| Stolen credentials | Vault rotation; single bearer token — rotation is a coordinated restart | **Medium** (single shared token) |
| Tenant data leakage | Unique constraints, ORM filtering | Low |
| Container breakout | cap_drop ALL, no-new-privileges | Low |
| Vault unavailability | **Fail-closed** — `django_core._credential` raises; never falls through to ENV | Medium (availability, not confidentiality) |
| Embedding quality bypass | Hash embeddings are deterministic but not semantic | Medium |
| DDoS on Vault | 5-min TTL cache | Low |
| Brute-force on bearer token | Constant-time compare only; **no rate limiting** | **Medium** |
| Unauthorized policy bypass via OPA | **N/A — no OPA gate exists.** Authorization is the bearer token. | Informational |

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

*End of SOMA-SFM-SEC-001 v2.1.0*
