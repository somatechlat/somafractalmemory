<!-- Canonical Roadmap for SomaFractalMemory (SFM) v2.1 -->

# SFM Canonical Roadmap (v2.1)

This document is the single source of truth for memory core evolution: math spec, principles, sprints, gating metrics, and deprecations. All future architectural changes MUST reconcile here.

## 0. Vision
Create the leanest, fastest, mathematically principled memory engine for Somabrain:
* Deterministic, auditable, reversible.
* Factorized scoring with bounded terms.
* Minimal dependencies and predictable latency from thousands to millions of memories.
* Complexity is justified only by measured improvement (latency / recall / footprint).

## 1. Principles
1. Simplicity first – no speculative abstraction.
2. Math integrity – explicit transformations, no hidden heuristics.
3. Observability over verbosity – aggregated metrics only.
4. Orthogonality – retrieval scoring ≠ retention policy.
5. Config contracts – safe defaults; advanced features require explicit flags.
6. Non‑destructive decay – use continuous factors; never mutate payloads to “age” them.
7. Truth tests only – no mock similarity; always real numeric operations.

## 2. Data Model (Internal)
| Field | Description |
|-------|-------------|
| id | Coordinate/UUID identifying memory |
| v | L2‑normalized vector (||v||₂ = 1) float32 |
| r | Raw importance (user/system supplied) |
| i | Normalized importance ∈ [0,1] |
| t_creation | Epoch creation time |
| t_access | Last access time (for retention) |
| access_count | Frequency counter (optional) |
| metadata | JSON‑safe dictionary |
| features F | Optional bounded feature channels f_j ∈ [0,1] (deferred) |

Contiguous slabs (fast core): V (N,D), I (N,), T (N,), optional A, C, ID mapping, capacity growth geometric.

## 3. Retrieval Math
Similarity (unit vectors): sim_raw = q·v; sim = max(0, sim_raw).
Importance normalization (logistic preferred): i = 1 / (1 + exp(-k(r-c))).
Importance exponent (later): i_adj = i^α (α=1 initial).
Decay (half‑life τ, disabled if τ=∞): decay = 2^{-Δt/τ}.
Feature channel (deferred): d = Π f_j^{w_j} with Σ w_j ≤ 1.
Final Score: Score = sim * i_adj * decay * d ∈ [0,1].
Log form for analysis: log Score = log(sim+ε) + α log i − (ln2/τ)Δt + Σ w_j log f_j.

## 4. Retention (Deferred)
RetentionScore R = γ₁ i_adj + γ₂ 2^{-(T_now−t_access)/τ_r} + γ₃ log(1+c)/log(1+C_max) − γ₄ cost.
Activated only when scale gates trip.

## 5. Hot Path Complexity
Flat index query: O(ND + N) (matmul + elementwise scaling + partial selection).
Top‑k: argpartition (O(N)) + local sort (k log k).

## 6. Deprecations
| Legacy | Status | Replacement |
|--------|--------|-------------|
| Destructive decay threads | Deprecated | Half‑life multiplicative factor |
| Constant score in-memory search | Deprecated | Real cosine + importance scaling |
| Raw importance ranking | Deprecated | Normalized importance i |
| Mutation-based pruning | Deprecated | Retention score (later) |

## 7. Gating Conditions
| Gate | Condition | Action |
|------|-----------|--------|
| G1 | N>200k & p95>25ms | Introduce hot tier + retention score |
| G2 | Importance skew extreme | Enable α tuning |
| G3 | Frequent top‑k ties | Add sim exponent β |
| G4 | Memory pressure | Float16 / projection |
| G5 | ANN backend | Residual penalty factor |
| G6 | Product needs aging | Enable τ half‑life |

## 8. Sprints (Rapid)
### Sprint 1 (Current)
* Enforce normalization @ insert.
* Real cosine similarity in in‑memory path.
* Importance normalization (min–max bootstrap → logistic later).
* Score = sim * i (decay stub = 1).
* Truth tests: norms, similarity monotonicity, clamp non‑negative.

### Sprint 2
* Contiguous slab arrays (V,I,T,ID) + direct matmul query path.
* Microbenchmark (N=5k,10k; k=5,10) p50/p95 capture.
* Replace legacy constant-scoring search fully.

### Sprint 3
* τ parameter + optional half‑life activation.
* Decay correctness tests (Δt=τ → ≈0.5).
* Latency regression guard (<5%).

### Sprint 4 (Conditional G1)
* RetentionScore implementation (no eviction until flagged enable).
* Synthetic evaluation for ordering.

### Sprint 5 (Conditional)
* Hot tier + eviction, metrics (hot_hit_ratio, promotions).

### Sprint 6 (Conditional)
* Float16 option + recall test.
* Projection / ANN adapters + residual penalty.

## 9. Metrics
total_vectors, insert_qps, query_qps, p50/p95 latency, norm_error_max, importance quantiles, decay_active%, (later) hot_tier_hit_ratio, eviction_count.

## 10. Test Matrix
| Test | Purpose | Sprint |
|------|---------|--------|
| test_norm_invariant | Vector normalization | 1 |
| test_similarity_monotonicity | Ranking correctness | 1 |
| test_zero_similarity_clamp | Safety | 1 |
| test_importance_present | Importance norm field set | 1 |
| test_half_life_halving | Decay correctness | 3 |
| test_retention_ordering | Retention math | 4 |
| test_float16_recall | Precision impact | 6 |

## 11. Risks & Mitigation
| Risk | Mitigation |
|------|------------|
| Importance shock | Log pre/post top‑k diff, fallback flag |
| Latency regression | Benchmark per sprint; rollback threshold 5% |
| Over‑eager retention | Gate by metrics (G1) |
| Approx recall loss | Residual penalty + recall@k baseline |

## 12. Acceptance (Core v2 Completion)
* Score pipeline stages 1–3 merged and tested.
* Benchmarks reproducible and documented.
* No destructive payload mutation for aging.
* Separation of retrieval & retention concerns codified.
* Roadmap kept synchronized with code changes.

---
Change Log:
* v2.1 (initial canonical roadmap committed) – Sprint 1 initialization.
