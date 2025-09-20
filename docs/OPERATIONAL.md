Operational Runbook for SomaFractalMemory
=========================================

Purpose

This runbook gives on-call engineers quick steps to diagnose common issues, reconcile WAL backlogs, inspect eviction behavior, and safely perform maintenance windows.

Quick checks

1. Health endpoints
   - Check API health (if enterprise): GET /health
   - Check metrics endpoint: GET /metrics

2. WAL backlog
   - Query `soma_wal_pending_count` and compare to `soma_eviction_index_size`.
   - If WAL backlog is growing, inspect logs for vector upsert errors (network/Qdrant auth issues).

3. Eviction surprises
   - Review recent eviction events: `soma_evictions_total` and `soma_eviction_index_size`.
   - If a large number of items are being evicted unexpectedly, verify environment evictions parameters: `SOMA_DECAY_*`, `SOMA_EVICTION_THRESHOLD`.

Reconciliation steps

- Manual WAL reconciliation (single run):
  1. Stop incoming write traffic (if possible).
  2. Run the reconciliation CLI: `python -m somafractalmemory.cli reconcile --once`.
  3. Monitor `soma_wal_pending_count` until it decreases.

- Rebuild eviction index
  - In case of index corruption:
    1. Export all memory keys using the `dump` CLI.
    2. Recompute eviction scores locally with `scripts/rebuild_eviction_index.py` (example script to add).

Maintenance operations

- Upgrading vector backend (Qdrant):
  - Drain writes, snapshot Qdrant collection, apply schema migrations, restore.

- Increasing capacity:
  - Tune `SOMA_MEMORY_LIMIT_BYTES` and `SOMA_MAX_PAYLOAD_BYTES`.

Contacting maintainers

- Include: last 1 hour of logs, current metrics for store/recall/eviction, last successful WAL reconciliation timestamp.
