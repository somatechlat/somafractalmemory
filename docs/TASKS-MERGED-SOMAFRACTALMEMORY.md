# SomaFractalMemory — Merged Tasks & Requirements

**Document:** TASKS-MERGED-SOMAFRACTALMEMORY.md
**Version:** 1.0.0
**Date:** 2026-01-03
**Source:** Merged from SRS-SOMAFRACTALMEMORY-MASTER.md and AGENT.md

---

## Quick Reference

| Metric | Value |
|--------|-------|
| Total Files | 53 |
| VIBE Compliance | 100% |
| Outstanding TODOs | 0 |
| Action Items | 0 |

---

## 1. Core Components (Status: ✅ Complete)

### 1.1 Data Models
| Model | Status | Notes |
|-------|--------|-------|
| Memory | ✅ | Fractal coordinates, PostgreSQL ArrayField |
| GraphLink | ✅ | Relationship storage |
| VectorEmbedding | ✅ | Milvus reference |
| MemoryNamespace | ✅ | Config and stats |
| AuditLog | ✅ | CRUD compliance |

### 1.2 Services
| Service | Status | Notes |
|---------|--------|-------|
| MemoryService (store/retrieve/search) | ✅ | Complete |
| GraphService (links/neighbors/paths) | ✅ | Complete |

### 1.3 API Endpoints
| Endpoint | Status |
|----------|--------|
| `POST /memories` | ✅ |
| `POST /memories/search` | ✅ |
| `GET /memories/{id}` | ✅ |
| `DELETE /memories/{id}` | ✅ |
| `GET /health` | ✅ |

---

## 2. Outstanding Tasks (None Critical)

### 2.1 Optimization (P2)
| Task | Effort | Status |
|------|--------|--------|
| Add memory eviction policy | 1d | ❌ Optional |
| Implement memory compression | 2d | ❌ Optional |
| Add batch insert endpoint | 0.5d | ❌ Optional |

### 2.2 Observability (P2)
| Task | Effort | Status |
|------|--------|--------|
| Prometheus metrics for memory ops | 0.5d | ⚠️ Partial |
| Memory size by namespace gauge | 0.25d | ❌ |
| Vector search latency histogram | 0.25d | ❌ |

---

## 3. Integration Tasks

### 3.1 SomaBrain Integration (Status: ✅ Complete)
| Task | Status |
|------|--------|
| HTTP endpoint stable | ✅ |
| Memory store/recall working | ✅ |
| Multi-tenant isolation | ✅ |

### 3.2 Capsule Integration (P1)
| Task | Effort | Status |
|------|--------|--------|
| Memory scoped to Capsule ID | 0.5d | ⚠️ Partial |
| Memory export per Capsule | 0.5d | ❌ |
| Memory redaction on Capsule delete | 0.5d | ❌ |

---

## 4. Test Coverage

| Area | Coverage | Action |
|------|----------|--------|
| Memory CRUD | 95% | ✅ OK |
| Graph operations | 90% | ✅ OK |
| Vector search | 85% | Add edge cases |
| Multi-tenant | 90% | ✅ OK |

---

## 5. Implementation Phases

### Phase 1: Capsule Integration (Week 1)
- [ ] Scope memory by Capsule ID
- [ ] Add export endpoint per Capsule

### Phase 2: Observability (Week 1-2)
- [ ] Complete Prometheus metrics
- [ ] Add latency histograms

### Phase 3: Optimization (Week 2+)
- [ ] Memory eviction
- [ ] Batch insert

---

## 6. Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `api/endpoints/memories.py` | MODIFY | Add Capsule scope |
| `services/store.py` | MODIFY | Capsule-aware storage |
| `api/endpoints/export.py` | CREATE | Capsule export |
| `metrics/exporters.py` | MODIFY | Add memory metrics |

---

**Total Effort Estimate:** 2-3 developer days

---

*END OF MERGED TASKS — SOMAFRACTALMEMORY*
