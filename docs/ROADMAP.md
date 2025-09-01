# Roadmap

This file captures the high-level plan and next milestones. It’s safe to sync with your own planning, and it won’t break code.

## Completed
- Hardened FAISS training semantics + exact rerank alignment.
- Unified WAL and reconcile loop; lifecycle/shutdown safety.
- Anomaly/range/math guards; salience/annealing/decay safeguards.
- Metrics and health checks; audit logging opt-in via env var.
- Optional novelty-based write gate (default off) to reduce write amplification.
- Decluttered repo; moved to standard src/ layout.
- All tests passing with 1 expected skip (HNSW buffering case).

## In Progress
- Validate packaging and editable install on fresh envs. (Working in local venv.)

## Next
- Implement hierarchical NumPy-only in-memory ANN index with exact re-rank.
  - Beam search over centroids, periodic rebuild hooks, metrics.
  - Feature-flag/profile via factory config; default remains simple in-memory.
  - Add unit tests and integrate with benchmark harness.
- Extend performance harness to include fractal_inmemory backend.
- Update README and CONFIGURATION docs for novelty gate and new backend.

## Stretch
- True Redlock support for distributed locks.
- Optional GPU FAISS path with configuration guards.
- More graph analytics (communities, centrality) behind an optional extra.

## Notes
- Keep core small; heavy deps live behind extras. Maintain graceful degradation when extras are missing.
- Favor classical, stable math and add tests for boundary cases.
