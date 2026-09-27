# SOMAFRACTALMEMORY — PROJECT EXECUTION PLAN

## Document Control

| Field | Value |
|-------|-------|
| Document Title | SomaFractalMemory Production Readiness Execution Plan |
| Document Identifier | SOMA-SFM-EXEC-001 |
| Version | 1.0.0 |
| Date | 2026-06-15 |
| Status | Active |
| Cross-Reference | SOMA-PM-CHARTER-001 (Master Project Charter) |

---

## 1. CURRENT STATE

| Metric | Value | Target |
|--------|-------|--------|
| Version | 0.2.0 | 0.3.0 |
| Maturity | Production Ready | Production Hardened |
| Python SLOC | ~5,135 | — |
| Test files | 14 | 20+ |
| TODO/FIXME | 0 | 0 |
| Security findings | 1 minor (timing side-channel) | 0 |
| Embedding quality | Hash-based (SHA-256) | ML-grade model |

---

## 2. EXECUTION TASKS

### Phase A: Documentation & Compliance (Weeks 1-4) — Parallel with SomaAgent01 Phases 1-2

| Task | Owner | Start | End | Deliverable |
|------|-------|-------|-----|-------------|
| SFM-A.1 Review and finalize ISO docs | SFM Team | Jun 16 | Jun 27 | All ISO docs reviewed, corrections applied |
| SFM-A.2 Update compatibility matrix | SFM Team | Jun 30 | Jun 30 | SOMA-SFM-COMPAT-001 current |
| SFM-A.3 Fix SimpleTokenAuth timing issue | SFM Team | Jul 1 | Jul 1 | auth.py:202 uses hmac.compare_digest |
| SFM-A.4 Clean up .env placeholder secrets | SFM Team | Jul 2 | Jul 3 | No placeholder secrets in .env |
| SFM-A.5 Documentation review gate | PM | Jul 7 | Jul 11 | Gate signed off |

### Phase B: Integration Support (Weeks 3-7) — Parallel with SomaAgent01 Phases 2-3

| Task | Owner | Start | End | Deliverable |
|------|-------|-------|-----|-------------|
| SFM-B.1 Verify SomaAgent01 HTTP integration | SFM Team | Jul 1 | Jul 4 | Agent→SFM store/recall working |
| SFM-B.2 Verify SomaBrain transport integration | SFM Team | Jul 7 | Jul 11 | Brain→SFM store/recall working |
| SFM-B.3 Verify sbk_* token validation | SFM Team | Jul 14 | Jul 16 | Brain tokens validated correctly |
| SFM-B.4 API backward compatibility review | SFM Team | Jul 21 | Jul 23 | No breaking changes in v0.2.x |
| SFM-B.5 Integration support gate | PM | Jul 28 | Jul 28 | Gate signed off |

### Phase C: Enhancement (Weeks 8-12) — Parallel with SomaAgent01 Phases 4-5

| Task | Owner | Start | End | Deliverable |
|------|-------|-------|-----|-------------|
| SFM-C.1 Evaluate embedding model upgrade | SFM Team | Aug 4 | Aug 11 | Technical assessment document |
| SFM-C.2 Add integration tests | SFM Team | Aug 4 | Aug 22 | 20+ test files |
| SFM-C.3 Verify K8s Helm charts | SFM Team | Aug 25 | Sep 1 | prod-ha values validated |
| SFM-C.4 Load testing (store/search throughput) | SFM Team | Sep 1 | Sep 5 | Performance baseline |
| SFM-C.5 Milvus index optimization | SFM Team | Sep 8 | Sep 12 | Tuned nlist/nprobe |
| SFM-C.6 Enhancement gate | PM | Sep 12 | Sep 14 | Gate signed off |

### Phase D: Validation (Weeks 14-16) — Parallel with SomaAgent01 Phase 6

| Task | Owner | Start | End | Deliverable |
|------|-------|-------|-----|-------------|
| SFM-D.1 Full AAAS integration test | SFM Team | Sep 15 | Sep 18 | SFM works in AAAS stack |
| SFM-D.2 Version compatibility validation | SFM Team | Sep 18 | Sep 19 | COMPAT matrix verified |
| SFM-D.3 Data integrity validation | SFM Team | Sep 22 | Sep 26 | Soft deletes, audit logs correct |
| SFM-D.4 Validation gate | PM | Oct 2 | Oct 5 | Gate signed off |

---

## 3. DEPENDENCIES ON OTHER REPOS

| Dependency | From | Impact | Mitigation |
|------------|------|--------|------------|
| SomaAgent01 testing SFM endpoints | somaAgent01 Phase 4 | Integration test results | SFM tests are independent |
| SomaBrain sbk_* token format | somabrain | Auth validation | Stable contract, unlikely to change |
| Milvus infrastructure | DevOps | Vector store tests blocked | Docker Milvus in CI |

---

## 4. RISKS

| ID | Risk | Score | Mitigation |
|----|------|-------|------------|
| SFM-R1 | Hash embedding quality insufficient for production | 12 | Evaluate ML model upgrade (SFM-C.1) |
| SFM-R2 | Milvus scaling under load | 12 | Load testing, index tuning, capacity planning |
| SFM-R3 | Vault unavailability blocks startup | 9 | Graceful fallback documented |
| SFM-R4 | Breaking API change in v0.3.0 | 8 | Semantic versioning, contract tests |

---

## 5. VERSION ROADMAP

| Version | Target Date | Key Changes |
|---------|-------------|-------------|
| 0.2.1 | Jul 2026 | Security fix (timing side-channel), .env cleanup |
| 0.2.2 | Aug 2026 | Additional tests, documentation updates |
| 0.3.0 | Oct 2026 | Embedding model upgrade (if approved), performance optimizations |

---

End of Document
