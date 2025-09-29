# Fast Core & Importance Normalization Math

This document details the math invariants for the fast core flat index and adaptive importance normalization pipeline.

---
## 1. Fast Core (Flat Index)
When `SFM_FAST_CORE=1` a contiguous in-process slab is maintained alongside the canonical vector store:

- `vectors`: `float32[capacity, D]` (L2-normalized rows)
- `importance`: `float32[capacity]` (already normalized to [0,1])
- `timestamps`: `float64[capacity]`
- `payloads`: Python list of payload dicts (reference only)

Search path:
1. Embed query `q` → L2-normalized vector.
2. Compute raw similarities `s_i = max(0, vectors_i · q)` (negative cosine values clamped to 0).
3. Multiply by normalized importance: `score_i = s_i * importance_i`.
4. `top_k` selection via `argpartition` (O(n)) + local sort of `k` indices (O(k log k)).

Rationale:
- Removes external RPC latency for small/medium corpora.
- Keeps branch-free inner loop (single fused matmul + clamp + multiply).
- Allows easy future extension (e.g., time decay weight) as an elementwise multiply.

---
## 2. Adaptive Importance Normalization
Raw importance values (`raw`) can have arbitrary scale and heavy-tailed distributions. We transform them into a bounded `[0,1]` `importance_norm`, chosen by a lightweight decision tree.

### 2.1 Reservoir & Quantiles
- Maintain a 512-sample reservoir of the most recent values.
- Recompute quantiles every 64 inserts: `q10, q50, q90, q99`.

### 2.2 Tail / Asymmetry Ratios
Let:
```
upper_core = q90 - q50
lower_core = q50 - q10
R_tail_max = (max - q90) / upper_core
R_tail_ext = (q99 - q90) / upper_core
R_asym     = (q90 - q50) / lower_core
```
(Each denominator guarded by epsilon.)

### 2.3 Decision Tree
1. Warm-up (<64 samples): plain min–max with running min/max.
2. If `R_tail_max ≤ 5` and `R_asym ≤ 3`: plain min–max.
3. Else if `R_tail_max ≤ 15` and `R_tail_ext ≤ 8`: winsorized scaling.
4. Else: logistic mapping.

### 2.4 Methods
#### Plain Min–Max
```
norm = (raw - min) / (max - min)
```
#### Winsorized Min–Max
```
spread = q90 - q10
L = max(min, q10 - 0.25 * spread)
U = min(max, q90 + 0.25 * spread)
raw' = clamp(raw, L, U)
norm = (raw' - L) / (U - L)
```
#### Logistic Mapping
```
spread = q90 - q10
k = ln(9) / spread   # slope so that (q10,q90) roughly map to ~0.1 and ~0.9
k capped to 25 for stability
c = q50              # midpoint
norm = 1 / (1 + exp(-k * (raw - c)))
```

### 2.5 Invariants
- `importance_norm ∈ [0,1]` (within floating tolerance).
- Monotonic in `raw` within each selected method region.
- Method changes only at insert time; recall path uses stored scalar (no branching).

---
## 3. Combined Retrieval Score
Currently:
```
score = max(0, cosine(q, v)) * importance_norm
```
Planned extensions (multiplicative factors, all unit-interval bounded):
```
score = cosine⁺ * importance_norm * time_decay * feature_weight
```
Where `cosine⁺ = max(0, cosine)` and `time_decay` may be `exp(-ln(2) * age / half_life)`.

---
## 4. Testing
`tests/test_fast_core_math.py` validates:
- Embedding normalization invariance.
- Cosine monotonicity ordering preserved.
- Importance normalization monotonicity across methods.
- Clamp safety for negative similarities.

Additional future tests: tail scenario synthetic datasets to assert method switching thresholds.

---
## 5. Operational Notes
- Fast core is append-only; deletions are not compacted yet (tombstoning could be added if needed).
- Reallocation doubles capacity to keep amortized O(1) append.
- Memory footprint: `capacity * (4*D + 4 + 8)` bytes plus Python object overhead; with D=768 and capacity=1M ≈ ~3.6 GB for vectors + metadata (plan tiered retention before reaching this scale).

---
Happy hacking.
