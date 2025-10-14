SomaBrain 3.0 Compliance Plan for SomaFractalMemory

Purpose
-------
This document is the canonical compliance plan to adapt SomaFractalMemory into a Memory Manager Data Plane that enforces the SomaBrain 3.0 invariants at the infrastructure layer.

Goals & Invariants
------------------
We will enforce the core mathematical and operational invariants:
- PSD Invariant: the density matrix ρ must be Positive Semi-Definite (PSD).
- Trace Normalization: tr(ρ) == 1 (within a configurable numeric tolerance).
- Latency Guard: ρ reads and critical matrix operations must meet p95 latency targets (example: <60ms).
- Purity: remove cognitive math (L2/norm-based recall, IsolationForest) from the data plane; re-home to a Manager process.
- Operational Truth: health and metrics must report mathematical correctness (PSD & trace) in addition to service liveness.
- Precise Pruning: pruning must be directed by Control Plane ordering (eigenvector orthogonality / Manager-provided ranking).

High-level Waves (Roadmap)
--------------------------
Wave 0 — Stabilize & Baseline (Immediate)
- Fix current repo compile errors and static-check failures.
- Ensure `v2.2.0` branch is green before adding invariant-enforcement code.

Wave 1 — Atomic ρ Commit & Matrix Serialization
- Extend the store API with an atomic matrix commit contract: `commit_matrix_update` / `commit_transaction(updates: Dict)`.
- Implement Postgres transactional storage (bytea / matrices table) and AsyncRedis atomic writes using Lua script (CAS semantics).
- Implement binary, versioned matrix serialization (np.ndarray -> base64 envelope) with compatibility fallback for existing JSON values.
- Provide unit tests and migration rules.

Wave 2 — Enforce Low-Latency ρ Caching & De-cognitization (Data-plane purity)
- Default ρ reads to `AsyncRedisKeyValueStore` (fast in-memory path) with Postgres fallback and degraded mode reporting.
- Introduce `SFM_DECOGNITIZE` feature-flag that disables cognitive math (IsolationForest, L2 recall) in the data plane and moves it to `cognitive_manager`.
- Add metrics to ensure p95 read latency targets are met.

Wave 3 — Operational Truth: Health, Metrics & Events
- Add PSD & trace norm checks, expose them via `/healthz` (HTTP) and Health RPC (gRPC).
- Add Prometheus gauges & histograms for PSD success and trace norm error, commit latency, and degraded mode.
- Publish `rho.status` events to Kafka with a schema in `schemas/`.

Wave 4 — Pruning & Control-Plane Integration
- Allow pruning to be directed by Control Plane ordering; accept pre-sorted prune lists over RPC/Kafka and apply them atomically to the datastore.
- Add contract and tests for prune ordering and fallback.

Wave 5 — CI, Docs, Canary Rollout & Cleanup
- Add CI gates for atomic commits, PSD checks, serialization tests, and optional integration tests.
- Update docs and migration guides; run canary rollout with alerting and runbooks; remove deprecated cognitive code in later cleanup PRs.

Detailed Task Breakdown (Sprint-ready items)
-------------------------------------------
1. Stabilize repo (Task owner: infra/dev)
- Files affected: `somafractalmemory/implementations/async_storage.py`, repo-wide small `isinstance` fixes.
- Acceptance: ruff/mypy PASS, unit tests for core features PASS.

2. Spec & API for atomic ρ commit
- Design `IKeyValueStore.commit_matrix_update(updates: Dict[str, bytes], metadata: Dict, expected_version: Optional[int])`.
- Document error semantics and retry policies.

3. Matrix serialization & migration
- Add `serialize_matrix(np.ndarray, version:int=1) -> envelope_bytes` and `deserialize_matrix(envelope_bytes)`.
- Envelope includes metadata: version, dtype, shape, timestamp, optional compression flag.
- Migration helper: `migrate_json_payload_to_matrix(key)`.

4. Postgres + Redis atomic implementations
- `PostgresKeyValueStore.commit_matrix_update` uses SERIALIZABLE transaction or advisory locks plus write-to-matrices table.
- `AsyncRedisKeyValueStore.commit_matrix_update` uses a Lua script to write multiple keys atomically and optionally check expected_version.
- `PostgresRedisHybridStore` coordinates writes for write-through semantics and invalidates caches.

5. ρ caching & factory wiring
- `factory.py` must ensure that when FD-sketch or ρ matrix is requested, service uses Redis async store by default.
- Add `SFM_RHO_CACHE_TTL` and `SFM_RHO_READ_TIMEOUT_MS` config keys.

6. De-cognitization
- Introduce a `cognitive_manager` module.
- Wrap existing cognitive calls in `core.py` and `minimal_core.py` with `if not SFM_DECOGNITIZE: ...`.
- Provide a compatibility shim to run the cognitive code as an external service during migration.

7. Health & metrics
- Add `somabrain_rho_psd_ok` gauge (0/1) and `somabrain_rho_trace_norm_error` gauge.
- Health endpoints to return structure: `{ "ok": true, "rho": {"psd_ok": true, "trace_error": 1.2e-9, "sample_version": 42}}`.
- Add event emitter to kafka `rho.status` with `{timestamp, node_id, psd_ok, trace_error, version}`.

8. Pruning contract
- Define prune message schema `prune.order` with list of keys ordered by Control Plane.
- `_enforce_memory_limit` to accept optional param `prune_order: list[str]`.

9. Tests & CI
- Unit tests (serialization, PSD checks, Lua script unit tests via fakeredis or Lua runner), integration tests using docker-compose.test.yml.

10. Docs & runbooks
- Update `docs/ARCHITECTURE.md`, `CONFIGURATION.md`, `PRODUCTION_READY_GAP.md`.
- Add `RUNBOOKS/RHO_VIOLATION.md` for operators.

Implementation notes and engineering constraints
-----------------------------------------------
- PSD check numeric tolerance: configurable epsilon (default 1e-8). Small negative eigenvalues within -epsilon should be clamped, but larger negatives should trigger alerts.
- Serialization: prefer float64 storage for accuracy; allow float32 option for throughput/space tradeoffs.
- Redis Lua scripts must be thoroughly unit-tested and loaded with EVALSHA and fallback to EVAL.
- Health checks must be inexpensive—compute PSD on a cached snapshot or run a sampled check.

Acceptance Criteria & Verification
----------------------------------
- Atomic commit tests ensure no partial writes; concurrency tests validate last-writer/wins or compare-and-swap depending on contract.
- Serialization round-trip error below configured tolerance.
- Health endpoints report PSD/trace metrics and metrics are exported to Prometheus.
- Canary deployment shows stable PSD/trace and low latencies before global rollout.

Rollout plan
------------
- Dark launch: add metrics and health checks in dark mode.
- Canary: enable Redis atomic path and commit in single canary cluster; monitor for 1–2 hours.
- Progressive rollout: expand canaries; once stable for the observation window, flip defaults and mark legacy cognitive code deprecated.

Appendix: immediate developer tasks (what I will start now if you say go)
------------------------------------------------------------------------
A. Fix the syntax error and run linters/tests (Wave 0). (In-progress)
B. Create the matrix serialization helpers and unit tests (start of Wave 1).
C. Draft Redis Lua script for atomic commits and unit test harness.


Document history
----------------
- Created: 2025-10-14
- Author: Compliance automation
