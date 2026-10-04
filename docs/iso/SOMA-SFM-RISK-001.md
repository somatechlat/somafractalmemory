# SOMA-SFM-RISK-001: SomaFractalMemory Risk Register

> **Standard**: ISO 31000:2018 — Risk Management — Guidelines
> **Owner**: SomaTech LAT

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SOMA-SFM-RISK-001: SomaFractalMemory Risk Register |
| Document Identifier | SOMA-SFM-RISK-001 |
| Version | 2.1.0 |
| Date | 2026-10-03 |
| Status | Draft |
| Author | SomaTech LAT Engineering |
| Approver | — |
| Classification | Confidential |
| ISO Reference | ISO 31000:2018 — Risk Management — Guidelines |
| Next Review | 2027-01-03 |
| Related | `somafractalmemory/settings/infra.py` (deleted-knob record) |

## Revision History

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 1.0.0 | 2025-10-01 | Engineering | Initial risk register |
| 2.0.0 | 2026-06-15 | Engineering | Updated for v0.2.0; added Vault availability, circuit breaker risks |
| 2.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-SFM-RISK-001` \| case normalised to `Approved` \| prior classification `PROPRIETARY / COMMERCIAL SENSITIVE` normalised to `Confidential`. |
| 2.1.0 | 2026-10-03 | SomaTech Engineering | Truth pass against the code. RISK-001 mitigation no longer cites the deleted `SOMA_FORCE_HASH_EMBEDDINGS` knob. RISK-003 corrected: Vault failure **raises** (no ENV fallback) — `settings/django_core._credential`. RISK-004 retitled: there is no SomaBrain auth client in this tree (`admin/aaas/auth.py` does not exist), so the risk is the AAAS integration's absence, not its outage. Circuit-breaker mitigation text removed (no breaker exists). Status returned to Draft (meaning change). |

---

## 1. Risk Assessment Methodology

### 1.1 Likelihood Scale

| Score | Label | Description |
|:------|:------|:------------|
| 1 | Rare | May occur only in exceptional circumstances |
| 2 | Unlikely | Could occur but not expected |
| 3 | Possible | Might occur at some point |
| 4 | Likely | Will probably occur in most circumstances |
| 5 | Almost Certain | Expected to occur frequently |

### 1.2 Impact Scale

| Score | Label | Description |
|:------|:------|:------------|
| 1 | Negligible | Minimal impact, easily absorbed |
| 2 | Minor | Some impact, manageable with standard procedures |
| 3 | Moderate | Noticeable impact, requires active management |
| 4 | Major | Significant impact on operations or quality |
| 5 | Critical | Threatens system viability or data integrity |

### 1.3 Risk Rating

| Rating | Score Range | Action Required |
|:-------|:-----------|:----------------|
| **LOW** | 1–4 | Monitor, accept |
| **MEDIUM** | 5–9 | Mitigate, plan response |
| **HIGH** | 10–15 | Immediate mitigation required |
| **CRITICAL** | 16–25 | Escalate, halt if necessary |

---

## 2. Risk Register

### RISK-001: Hash-Based Embedding Quality

| Field | Value |
|:------|:------|
| **Risk ID** | RISK-001 |
| **Category** | Technical / Quality |
| **Description** | The `HashEmbedder` generates deterministic but semantically meaningless vectors. Two conceptually related texts ("dark mode" / "night theme") produce completely unrelated embeddings. This degrades semantic search recall quality. |
| **Likelihood** | 5 (Almost Certain) |
| **Impact** | 3 (Moderate) |
| **Rating** | **HIGH (15)** |
| **Source** | `somafractalmemory/admin/core/services.py:27-42` |
| **Current Controls** | Hash embeddings are deterministic and L2-normalized; ORM fallback with GIN-indexed JSONB payload search |
| **Mitigation** | Replace with sentence-transformer model (e.g., `all-MiniLM-L6-v2`). The precomputed-embedding contract is the real path; `HashEmbedder` is the documented fallback when no vector is supplied. `SOMA_FORCE_HASH_EMBEDDINGS` was deleted: there is no second embedder to force off. |
| **Owner** | ML Engineering Lead |
| **Target Date** | v0.3.0 |

### RISK-002: Milvus Scaling Limitations

| Field | Value |
|:------|:------|
| **Risk ID** | RISK-002 |
| **Category** | Technical / Scalability |
| **Description** | Milvus standalone deployment (single node, IVF_FLAT index) may not scale to millions of vectors. Index rebuilds on large collections can cause latency spikes. The 4GB memory limit may be insufficient at scale. |
| **Likelihood** | 3 (Possible) |
| **Impact** | 4 (Major) |
| **Rating** | **HIGH (12)** |
| **Source** | `infra/standalone/docker-compose.yml:154-185` |
| **Current Controls** | Health checks with 180s start period; resource limits configured; ORM fallback when Milvus unavailable |
| **Mitigation** | 1) Monitor Milvus memory usage and collection sizes. 2) Plan migration to Milvus distributed mode or cloud-managed vector DB. 3) Implement collection partitioning by namespace. 4) Evaluate IVF_SQ8 or HNSW index for better memory efficiency. |
| **Owner** | Infrastructure Lead |
| **Target Date** | v0.3.0 |

### RISK-003: Vault Availability Dependency

| Field | Value |
|:------|:------|
| **Risk ID** | RISK-003 |
| **Category** | Operational / Availability |
| **Description** | SFM fetches database and Redis credentials from HashiCorp Vault at startup. If Vault is unreachable, `settings.django_core._credential` **raises** — there is no ENV fallback and never a code default. A Vault outage is an availability failure for the API, not a silent degradation to stale env values. Runtime credential rotation requires container restart. |
| **Likelihood** | 3 (Possible) |
| **Impact** | 4 (Major) |
| **Rating** | **HIGH (12)** |
| **Source** | `somafractalmemory/admin/core/security/vault_client.py`, `somafractalmemory/settings/django_core.py` (`_credential`) |
| **Current Controls** | Vault error raises (fail-closed); 5-min TTL cache prevents runtime Vault overload; Vault init container auto-mounts secrets |
| **Mitigation** | 1) Implement Vault HA (Raft consensus or external HA backend). 2) Add Vault health check to SFM readiness probe. 3) Automate secret rotation with Vault Agent sidecar. Note: pre-populating ENV as warm-standby is **prohibited** — a secret in the process environment is visible in `ps` and `/proc/*/environ` (Rule 164). |
| **Owner** | SRE Lead |
| **Target Date** | v0.2.5 |

### RISK-004: AAAS Auth Integration Does Not Exist

| Field | Value |
|:------|:------|
| **Risk ID** | RISK-004 |
| **Category** | Integration / Scope |
| **Description** | Earlier revisions described a SomaBrain `sbk_*` token-validation client in `somafractalmemory/admin/aaas/auth.py`, with a 3s timeout and local `sfm_*` key fallback. **None of that code exists.** `APIKey`/`UsageRecord` were dropped in migration `0006`. The only authentication in this tree is the standalone `SOMA_API_TOKEN` bearer. If AAAS multi-tenant auth is a product requirement, it is unimplemented, not degraded. |
| **Likelihood** | 5 (Almost Certain) |
| **Impact** | 4 (Major) |
| **Rating** | **HIGH (20)** |
| **Source** | `somafractalmemory/api/auth.py:1-9` ("STANDALONE mode only… No API key management, no SomaBrain integration"); `somafractalmemory/migrations/0006_drop_apikey_usagerecord.py` |
| **Current Controls** | Standalone bearer token only. Documentation now states AAAS as not deployed (`SOMA-SFM-ARCH-001` §2.2). |
| **Mitigation** | If AAAS is required: specify the auth contract first, then implement a client. Do not document a gate that does not exist. A circuit breaker around a non-existent client is not a mitigation. |
| **Owner** | Integration Lead |
| **Target Date** | v0.3.0 |

---

## 3. Lower-Priority Risks

### RISK-005: No TLS Between Internal Services

| Field | Value |
|:------|:------|
| **Risk ID** | RISK-005 |
| **Category** | Security / Network |
| **Description** | Internal Docker network traffic (API ↔ PostgreSQL, API ↔ Milvus, API ↔ Redis) is unencrypted. Sensitive data (credentials, memory payloads) transmitted in plaintext within the container network. |
| **Likelihood** | 2 (Unlikely) |
| **Impact** | 3 (Moderate) |
| **Rating** | **MEDIUM (6)** |
| **Mitigation** | 1) Add TLS termination for PostgreSQL, Redis, and Milvus. 2) Use Istio/Linkerd service mesh for mTLS. 3) Network policies in Kubernetes to restrict pod-to-pod communication. |
| **Owner** | Infrastructure Lead |
| **Target Date** | v0.3.0 |

### RISK-006: Audit Log Unbounded Growth

| Field | Value |
|:------|:------|
| **Risk ID** | RISK-006 |
| **Category** | Operational / Storage |
| **Description** | Every memory operation (create, read, update, delete, search) writes an `AuditLog` record. At high throughput, this table will grow without bound, degrading query performance and consuming storage. |
| **Likelihood** | 4 (Likely) |
| **Impact** | 2 (Minor) |
| **Rating** | **MEDIUM (8)** |
| **Mitigation** | 1) Implement table partitioning by timestamp. 2) Archive records older than retention period to cold storage. 3) Add database monitoring for table size alerts. |
| **Owner** | DBA Lead |
| **Target Date** | v0.2.5 |

### RISK-007: Redis Cache Stampede on Cold Start

| Field | Value |
|:------|:------|
| **Risk ID** | RISK-007 |
| **Category** | Technical / Performance |
| **Description** | After a Redis restart or cache flush, all concurrent requests may simultaneously miss the cache and hit PostgreSQL, causing a stampede that degrades response times. |
| **Likelihood** | 2 (Unlikely) |
| **Impact** | 3 (Moderate) |
| **Rating** | **MEDIUM (6)** |
| **Mitigation** | 1) Implement cache-aside pattern with locking (stale-while-revalidate). 2) Warm cache on startup. 3) Set appropriate TTLs on cached entries. |
| **Owner** | Performance Lead |
| **Target Date** | v0.3.0 |

### RISK-008: `.env` Placeholder Secrets in Repository

| Field | Value |
|:------|:------|
| **Risk ID** | RISK-008 |
| **Category** | Security / Secrets |
| **Description** | `.env.example` contains `change-me` placeholder values. If an operator copies this directly without changing values, the deployment runs with known weak credentials. |
| **Likelihood** | 3 (Possible) |
| **Impact** | 4 (Major) |
| **Rating** | **HIGH (12)** |
| **Source** | `.env.example` |
| **Current Controls** | `.gitignore` excludes `.env`; `.env.example` is clearly marked as template |
| **Mitigation** | 1) Add startup validation that rejects known placeholder values. 2) Generate random secrets in deployment scripts. 3) Use Vault exclusively in production (no env var fallback). |
| **Owner** | DevOps Lead |
| **Target Date** | v0.2.5 |

---

## 4. Risk Heat Map

```
Impact
  5 │           │           │           │           │
    │           │           │           │           │
  4 │           │           │  RISK-002  │           │
    │           │           │  RISK-003  │           │
    │           │           │  RISK-004  │           │
    │           │           │  RISK-008  │           │
  3 │           │  RISK-005 │           │           │
    │           │  RISK-007 │           │ RISK-001   │
  2 │           │           │  RISK-006  │           │
    │           │           │           │           │
  1 │           │           │           │           │
    └───────────┴───────────┴───────────┴───────────┘
        1           2           3           4           5
                        Likelihood
```

---

## 5. Risk Summary

| Risk ID | Title | Rating | Trend | Owner |
|:--------|:------|:-------|:------|:------|
| RISK-001 | Hash embedding quality | HIGH | → | ML Engineering |
| RISK-002 | Milvus scaling | HIGH | → | Infrastructure |
| RISK-003 | Vault availability | HIGH | ↓ | SRE |
| RISK-004 | AAAS auth integration does not exist | HIGH | → | Integration |
| RISK-005 | No internal TLS | MEDIUM | → | Infrastructure |
| RISK-006 | Audit log growth | MEDIUM | ↑ | DBA |
| RISK-007 | Redis stampede | MEDIUM | → | Performance |
| RISK-008 | Placeholder secrets | HIGH | ↓ | DevOps |

### Trend Legend
- ↑ Increasing risk
- → Stable
- ↓ Decreasing risk (mitigations in progress)

---

## 6. Review Schedule

| Review Type | Frequency | Next Review |
|:------------|:----------|:------------|
| Risk register update | Quarterly | 2026-09-15 |
| High-risk item review | Monthly | 2026-07-15 |
| Post-incident review | As needed | — |
| Annual risk assessment | Annually | 2027-06-15 |

---

*End of SOMA-SFM-RISK-001 v2.1.0*
