# Cognitive Memory Design & Adaptive Normalization

> Status: Design document (spec) – implementation of temporal weighting, monotonic calibration guard, unified retrieval scoring, and metrics is pending.

## 1. Purpose
This document specifies mathematically precise mechanisms for evolving the existing Soma Fractal Memory (SFM) system into a transparent, testable, adaptive memory substrate. It avoids any unverifiable “cognitive mimicry” and focuses on:

* Adaptive importance normalization resilient to distribution drift.
* Temporal weighting of the importance reservoir.
* Monotonic calibration guard to preserve ordering semantics.
* Unified multi-factor retrieval scoring.
* Structured consolidation (episodic → semantic) without generative hallucination.
* Formal invariants and metrics for observability.

## 2. Current Baseline Summary
| Layer | Mechanism | Notes |
|-------|-----------|-------|
| Storage | Postgres canonical + Redis cache | JSON-first durability |
| Vector Index | Qdrant (cosine normalized embeddings) | Hash fallback available |
| Graph | NetworkX (unweighted) | Links added explicitly |
| Importance | Adaptive (minmax → winsor → logistic) | Uniform quantiles |
| Eventing | Kafka `memory.events` | One event per store attempt |
| Fast Core | Optional slab (flat vectors) | Acceleration path |

## 3. Canonical Memory Object
Each memory \( m \):
\[
m = \{ id, c, t, \text{payload}, I_{\text{raw}}, I_{\text{norm}}, \text{memory\_type}, \text{optional facets}\}
\]
Where:
* Coordinate \( c \in \mathbb{R}^d \)
* Timestamp \( t \in \mathbb{R}_{\ge 0} \)
* Raw importance \( I_{\text{raw}} \ge 0 \)
* Normalized importance \( I_{\text{norm}} \in [0,1] \)
* Embedding \( \mathbf{e} = \text{Embed}(\text{serialize}(\text{payload})) \), L2-normalized.

## 4. Adaptive Importance Normalization (Existing)
Decision tree (current):
1. Reservoir collects \( I_1..I_n \), capped size.
2. Compute quantiles: \( q_{10}, q_{50}, q_{90}, q_{99} \).
3. Tail ratios:
\[
R_{\text{tail\_max}} = \frac{\max(I)-q_{90}}{q_{90}-q_{50}+\varepsilon}, \quad R_{\text{tail\_ext}} = \frac{q_{99}-q_{90}}{q_{90}-q_{50}+\varepsilon}, \quad R_{\text{asym}} = \frac{q_{90}-q_{50}}{q_{50}-q_{10}+\varepsilon}
\]
4. Method selection:
* Plain minmax if \( R_{\text{tail\_max}} \le 5 \land R_{\text{asym}} \le 3 \)
* Winsor otherwise if moderate tail
* Logistic if extreme tail

## 5. Temporal Weighting (Planned Enhancement)
Uniform quantiles replaced by weighted quantiles using exponential decay weights:
\[
w_i = e^{-\lambda (t_{now} - t_i)} \quad (\lambda = \ln 2 / T_{1/2})
\]
Weighted quantile \( \tilde{q}_p \) is the smallest \( I_{(k)} \) where cumulative weight ratio \( \ge p \).
Tail ratios redefined with weighted quantiles:
\[
R_{\text{tail\_max}} = \frac{I_{\max}-\tilde{q}_{90}}{\tilde{q}_{90}-\tilde{q}_{50}+\varepsilon}\; ; \; R_{\text{tail\_ext}} = \frac{\tilde{q}_{99}-\tilde{q}_{90}}{\tilde{q}_{90}-\tilde{q}_{50}+\varepsilon}\; ; \; R_{\text{asym}} = \frac{\tilde{q}_{90}-\tilde{q}_{50}}{\tilde{q}_{50}-\tilde{q}_{10}+\varepsilon}
\]

### Advantages
* Recent distribution shifts have larger influence.
* Early outliers decay naturally.
* No hard reset required.

## 6. Monotonic Calibration Guard
Goal: ensure sequences of increasing \( I_{raw} \) do not produce decreasing \( I_{norm} \) beyond a negligible tolerance.

Sliding buffer of last \( M \) pairs \( (I_{raw}, I_{norm}) \) within a stable method regime. If a violation is detected:
* Apply isotonic regression (Pool Adjacent Violators) to obtain \( z_1 \le z_2 \le \ldots \le z_M \) minimizing \( \sum (z_i - I_{norm,i})^2 \).
* Rewrite adjusted normalized values for fast core / in-memory representation.
* Emit metric increment.

Freeze method switching temporarily if too many adjustments occur in a short insertion window (stability control).

## 7. Unified Retrieval Scoring (Planned)
Proposed composite score:
\[
S(m|q) = \alpha \cdot \text{sim}(\mathbf{e}_q, \mathbf{e}_m) + \beta \cdot I_{norm} + \gamma \cdot C(m,q) + \delta \cdot G(m) - \eta \cdot D(\Delta t)
\]
Where:
* \( \text{sim} = \max(0, \cos(\mathbf{e}_q, \mathbf{e}_m)) \)
* \( C(m,q) \) – context/facet match (binary or soft score)
* \( G(m) \) – graph relevance (e.g. weighted adjacency centrality)
* \( D(\Delta t) = 1 - e^{-\lambda_t \Delta t} \) (time decay)
* Coefficients initially static; future: adaptive tuning.

## 8. Consolidation (Non-Generative)
Semantic summary construction over window \( W \):
1. Collect episodic memories in \( W \).
2. Extract frequent facets / keys / tasks.
3. Build summary object referencing source coordinates:
```
{
  "fact": "Top facets: task=...",
  "source_coord": [...],
  "memory_type": "semantic"
}
```
No synthesis beyond enumeration, preserving reversibility.

## 9. Graph Elevation
Edge weight candidate:
\[
w_{i,j} = \alpha_f f_{co} + \alpha_t e^{-\lambda_t |t_i - t_j|} + \alpha_c \cdot \text{facet\_overlap}(i,j)
\]
Graph relevance contribution:
\[
G(m) = \frac{1}{Z} \sum_{k \in N(m)} w_{m,k} I_{norm}^{(k)}
\]

## 10. Feedback Modulation (Future)
Outcome error rate per facet:
\[
R_{facet} = 1 - \frac{errors_{facet}}{trials_{facet}+\varepsilon}\quad ; \quad I'_{norm} = I_{norm} \cdot R_{facet}
\]

## 11. Invariants
| Invariant | Description | Enforcement |
|-----------|-------------|-------------|
| Referential integrity | Semantic summaries reference existing episodics | Validation pass |
| Idempotent vector writes | Duplicate (coord,payload) avoids duplicate index entry | ID dedupe strategy |
| Monotonic batch | Increasing raw \(\Rightarrow\) non-decreasing norm (within tolerance) | Calibration guard |
| Tail reactivity | Weighted q90 shifts faster than uniform after drift | Drift test harness |
| Event uniqueness | Exactly one event per canonical store | Offset audit |

## 12. Metrics Specification
| Metric | Type | Labels | Meaning |
|--------|------|--------|---------|
| `soma_importance_weighted_q` | Gauge | `quantile` | Weighted quantiles (10,50,90,99) |
| `soma_importance_tail_ratio` | Gauge | `type` (max,ext,asym) | Tail profile ratios |
| `soma_importance_method_switch_total` | Counter | `from`,`to` | Normalization method transitions |
| `soma_importance_monotonic_adjustments_total` | Counter | - | Isotonic corrections applied |
| `soma_importance_freeze_active` | Gauge | - | Freeze state (0/1) |
| `soma_importance_recent_violations` | Gauge | - | Violations in rolling window |
| `soma_retrieval_score_component` | Histogram | `component` | Distribution of per-component contributions |

## 13. Parameters
| Name | Default | Notes |
|------|---------|-------|
| `reservoir_max` | 512 | Cap on importance samples |
| `recompute_interval` | 64 inserts | Weighted quantile refresh cadence |
| `half_life_inserts` | 256 | Derives decay \(\lambda\) |
| `monotonic_buffer` | 16 | Recent (raw,norm) pairs |
| `monotonic_tolerance` | 1e-8 | Float noise guard |
| `monotonic_max_adjust` | 3 / 256 inserts | Stability threshold |
| `method_freeze_len` | 32 | Cooling period after turbulence |

## 14. Test Matrix (Planned)
| Test | Focus | Pass Criteria |
|------|-------|--------------|
| Drift adaptation | Temporal weighting | Weighted q90 converges < uniform q90 time |
| Tail escalation | Extreme outlier injection | Method escalation (minmax→winsor/logistic) |
| Monotonic batch | Strictly increasing raw | No regressions or ≤ 1 isotonic adjustment |
| Freeze trigger | Oscillatory extremes | Freeze flag set, method stable |
| Score decomposition | Composite retrieval | Sum of components equals final score |

## 15. Implementation Phases
1. Introduce weighted quantiles + metrics (feature flag).
2. Integrate into method selection.
3. Add monotonic guard + isotonic correction.
4. Emit metrics (tail ratios, adjustments, switches).
5. Unified retrieval scoring plumbing (return detailed breakdown on recall endpoints internally or via debug flag).
6. Consolidation (non-generative) prototype.
7. Feedback modulation (reliability weighting).

## 16. Failure Modes & Safeguards
| Failure | Detection | Fallback |
|---------|-----------|----------|
| Weight underflow | Total weight < 1e-9 | Revert to uniform quantiles for cycle |
| Excess adjustments | Counter > threshold | Freeze method switching |
| Logistic overflow | `exp()` overflow | Clamp k / branch to step function |
| Reservoir poisoning | Raw > high watermark | Clamp before insert |

## 17. Non-Goals
* No generative semantic synthesis (keeps provenance guarantees).
* No hidden stochastic learning (all adaptive steps explicit & inspectable).

## 18. Security & Integrity
* All new metrics side-effect free.
* No mutation of canonical Postgres JSON on isotonic corrections (only affects transient fast-core / reporting).

## 19. Open Questions (Deferred)
| Question | Consideration |
|----------|---------------|
| Adaptive coefficient tuning | Requires labeled relevance dataset / offline evaluation harness. |
| Dynamic facet weighting | Could integrate TF-IDF style weighting into retrieval component \( C(m,q) \). |
| Cross-namespace consolidation | Governance & multi-tenant isolation concerns. |

## 20. Summary
This specification formalizes forthcoming adaptive enhancements while preserving the system’s auditability. Every adjustment is grounded in explicit formulas, bounded behavior, and testable invariants. Implementation can proceed incrementally under feature flags without breaking existing workloads.
