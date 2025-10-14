SomaFractalMemory — SomaBrain 3.0 Canonical Roadmap (Sprinted)
=============================================================

This is the canonical, sprinted roadmap that turns the current SomaFractalMemory
repo into a strict Memory Manager Data Plane compliant with SomaBrain 3.0
invariants. It is the single source of truth for the engineering pass.

Goals
-----
- Enforce the seven SomaBrain 3.0 invariants (PSD, Trace Normalization, Latency
  Guard, Purity, Operational Truth, Precision, Stability).
- Make the data plane simple, auditable, and mathematically correct: Postgres
  canonical KV, Redis low-latency cache + atomic ops, Qdrant vector store.
- Provide clear, tested, reversible rollout steps and CI gates.

How to use this document
------------------------
- Each Wave describes a set of Sprints. Each Sprint is 1–5 workdays and contains
  concrete tasks, changed files, tests, and acceptance criteria.
- The tracked todo list in the repository maps these sprints to actionable items.
- No destructive deletion of large sets of files should be performed without a
  separate explicit approval step; deletions are staged and reviewed.

Wave 0 — Stabilize, baseline, and safety (Day 0–2)
-------------------------------------------------
Sprint 0.1 — Repo stabilization (0.5–1 day)
- Tasks:
  - Fix syntax errors and pre-commit failures (already started).
  - Ensure imports succeed and run a focused subset of unit tests.
  - Ensure `somafractalmemory.serialization` and `async_storage` compile.
- Files: `implementations/async_storage.py`, `serialization.py`, `core.py`.
- Acceptance:
  - `python -c 'import somafractalmemory'` returns without exception.
  - Pre-commit hooks (black, ruff) pass locally.

Sprint 0.2 — Canonical roadmap check-in (0.5 day)
- Tasks:
  - Commit and lock the canonical roadmap document to `docs/SOMABRAIN_3_0_CANONICAL_ROADMAP.md`.
  - Update tracked todo list to reflect sprint breakdowns and owners.
- Acceptance:
  - Roadmap file present in `docs/` and referenced by top-level README.

Wave 1 — Purity & Serialization (Days 1–7)
-----------------------------------------
Sprint 1.1 — Remove in-data-plane cognitive math (1–2 days)
- Tasks:
  - Remove `recall` from `minimal_core.py`.
  - Remove `IsolationForest` import and usage in `core.py`.
  - Remove `find_shortest_path` from `interfaces/graph.py` and document deprecation for implementations.
- Files: `minimal_core.py`, `core.py`, `interfaces/graph.py`, implementations that reference removed methods must be flagged.
- Acceptance:
  - No runtime codepaths in the API call cognitive math in the data plane.
  - Unit tests referencing removed functions are updated or skipped behind a feature flag `SFM_DECOGNITIZE`.

Sprint 1.2 — Add robust NumPy serialization (1–2 days)
- Tasks:
  - Add envelope-based Base64 serialization for `np.ndarray` in `serialization.py`.
  - Add unit tests for round-trip accuracy (float64 default) and error bounds.
- Files: `serialization.py`, `tests/test_serialization.py` (new).
- Acceptance:
  - Roundtrip max absolute error < 1e-9 for float64; trace exactness for identity matrices.

Wave 2 — Atomic ρ Commit & Storage (Days 3–14)
---------------------------------------------
Sprint 2.1 — IKeyValueStore commit_transaction interface (2 days)
- Tasks:
  - Define `commit_transaction(self, updates: Dict[str, bytes], metadata: dict | None = None, expected_version: int | None = None) -> CommitResult` in `interfaces/storage.py`.
  - Add tests describing expected semantics (idempotency, CAS requirements, error codes).
- Files: `interfaces/storage.py`, `tests/test_commit_transaction.py` (new).
- Acceptance:
  - Interface documented and covered by unit tests.

Sprint 2.2 — Redis Lua atomic commit (3 days)
- Tasks:
  - Implement `commit_transaction` in `AsyncRedisKeyValueStore` using a Lua script that writes multiple keys atomically and supports expected_version check.
  - Provide a small Python wrapper to EVALSHA and fallback to EVAL when needed.
  - Unit test Lua semantics with local Redis (fakeredis or real Redis in CI).
- Files: `implementations/async_storage.py`, `scripts/test_lua_commit.sh` (helper), `tests/test_lua_commit.py`.
- Acceptance:
  - Concurrent writers using expected_version semantics produce deterministic results; no partial key writes observed.

Sprint 2.3 — Postgres canonical commit & hybrid coordination (3 days)
- Tasks:
  - Implement `commit_transaction` in `PostgresKeyValueStore` (transactional write to `kv_store` or dedicated `matrices` table, writing new version metadata atomically).
  - Update `PostgresRedisHybridStore` to coordinate writes: write to Postgres then call Redis commit script or use Redis as a CAS preconditioner.
  - Add migration docs for existing keys and versioning.
- Files: `implementations/storage.py`, `implementations/async_storage.py`, `factory.py`.
- Acceptance:
  - End-to-end test: commit updated ρ data via API; Postgres contains final version; Redis cache set; reads return consistent data.

Wave 3 — Latency Guard & Cache (Days 10–18)
-----------------------------------------
Sprint 3.1 — Fast rho cache enforcement (2–3 days)
- Tasks:
  - Modify `factory.create_memory_system` to pass a `rho_kv_store` (direct Redis client wrapper) into `SomaFractalMemoryEnterprise`.
  - Add config flags `SFM_RHO_READ_TIMEOUT_MS` and `SFM_RHO_CACHE_TTL`.
  - Add telemetry for p95 read latency.
- Files: `factory.py`, `core.py`, `config` settings.
- Acceptance:
  - Under synthetic load p95 rho read < 60ms for target dataset.

Sprint 3.2 — Fallback and degraded mode (1 day)
- Tasks:
  - If Redis unavailable, fallback to Postgres read and emit `somabrain_rho_degraded_mode=1` metric.
  - Add alerting thresholds for degraded mode.
- Acceptance:
  - Fallback path works and metrics reflect degraded state.

Wave 4 — Operational Truth & Metrics (Days 14–22)
-----------------------------------------------
Sprint 4.1 — PSD & Trace health checks (2–3 days)
- Tasks:
  - Add PSD and trace checks that run on a cached snapshot of ρ (not on critical request path) and expose results to `/healthz` and Prometheus.
  - Implement `somabrain_rho_psd_ok` and `somabrain_rho_trace_norm_error` gauges.
- Files: `http_api.py`, `core.py`, `metrics` wiring.
- Acceptance:
  - `/healthz` returns JSON with `psd_ok` and `trace_error` fields; Prometheus exposes matching gauges.

Sprint 4.2 — rho.status Kafka event (optional) (1–2 days)
- Tasks:
  - If eventing enabled, implement `rho.status` event producer in `eventing/producer.py` that publishes PSD/trace results.
  - Add schema to `schemas/` and consumer smoke-test.
- Files: `eventing/producer.py`, `schemas/memory.event.json`.
- Acceptance:
  - kafka topic receives `rho.status` messages in canary runs.

Wave 5 — Pruning & Control Plane Integration (Days 20–30)
---------------------------------------------------------
Sprint 5.1 — Pruning contract & API (2–3 days)
- Tasks:
  - Modify `_enforce_memory_limit` in `core.py` to accept an optional `prune_order: list[str]` param.
  - If prune_order provided, use it; otherwise use safe local fallback.
  - Document JSON RPC or Kafka schema used to pass prune_order.
- Files: `core.py`, `http_api.py` (or producer/consumer contract docs).
- Acceptance:
  - Integration test where Control Plane sends prune order and SFM applies it atomically.

Sprint 5.2 — Control Plane back-pressure & safety (2 days)
- Tasks:
  - Add checks to avoid accidental mass deletion (guard thresholds, dry-run mode).
  - Add audit logging for prune operations.
- Acceptance:
  - Deletes require explicit confirmation when above threshold; audit entries created.

Wave 6 — CI, Docs, Canary & Cleanup (Days 25–40)
------------------------------------------------
Sprint 6.1 — CI gates & integration tests (3–5 days)
- Tasks:
  - Add CI job to run unit tests, serialization tests, Lua script tests with ephemeral Redis, Postgres, and Qdrant in docker-compose.test.yml.
  - Add integration smoke job that runs memory-api with minimal infra and validates `/healthz` metrics.
- Files: `.github/workflows/ci.yml`, `docker-compose.test.yml`, test harnesses.
- Acceptance:
  - CI passes; integration tests run in CI or local runner.

Sprint 6.2 — Docs & Runbooks (2–3 days)
- Tasks:
  - Finalize `docs/ARCHITECTURE.md`, `PRODUCTION_READY_GAP.md`, add `RUNBOOKS/RHO_VIOLATION.md`.
  - Provide step-by-step canary rollout and rollback steps.
- Acceptance:
  - Documentation approved and linked from README.

Sprint 6.3 — Cleanup & remove deprecated cognitive code (2–4 days)
- Tasks:
  - After observation window, remove deprecated cognitive code blocks and drop `SFM_DECOGNITIZE` flags.
  - Update CHANGELOG and bump version to v3.0.0-memory-manager.
- Acceptance:
  - Final codebase contains only data-plane functionality; cognitive manager runs externally as a separate repo/service.

Operational cadence & owners
---------------------------
- Each sprint should have a named owner (developer or team). Default: you (repo owner) or an assigned engineer.
- Daily standups and CI gating per sprint are recommended.

Estimates & timeline
--------------------
- Conservative estimate: 25–40 engineering days across all sprints (1–3 engineers).
- Early-value sprints (0–2) deliver strong ROI (stability and serialization).

Next immediate actions (I will execute once you confirm)
-----------------------------------------------------
1. Mark Sprint 1.1 as in-progress in the tracked todo list (done if you want).
2. Run a local in-memory smoke test of the API on port 9595 (uvicorn) using an auto token. (Requires Python deps.)
3. Or create ephemeral docker-compose minimal context and run memory-api + Postgres + Redis + Qdrant for end-to-end smoke test.

Change control & destructive actions
-----------------------------------
- All destructive deletions beyond the ones already performed will be gated behind an explicit confirmation step. The roadmap supports a staged approach: soft-archive → test → hard-delete.

Document history
----------------
- Created: 2025-10-14
- Author: Canonical roadmap generator (saved to `docs/SOMABRAIN_3_0_CANONICAL_ROADMAP.md`)
