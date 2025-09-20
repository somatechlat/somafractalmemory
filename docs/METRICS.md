Metrics for SomaFractalMemory
=============================

This document describes the Prometheus metrics exposed by SomaFractalMemory, example PromQL queries, and alerting/recording rule suggestions.

Design Principles

- Low-cardinality labels. Use `namespace`, `backend` and `component` as optional labels only when necessary.
- Counters for operations (store, recall, vector_upsert, wal_events).
- Histograms for latency-critical operations (store_latency_seconds, recall_latency_seconds).
- Gauges for internal sizes (eviction_index_size, wal_pending_count).

Metrics exposed

- soma_store_total{namespace=""} (counter)
  - Total number of memory store operations accepted by the core.

- soma_recall_total{namespace=""} (counter)
  - Total number of recall requests (semantic or coordinate).

- soma_vector_upsert_total{backend="qdrant|memory"} (counter)
  - Number of vector upserts attempted.

- soma_store_latency_seconds (histogram)
  - End-to-end latency for the store path (serialize -> kv write -> vector upsert -> eviction index update).

- soma_recall_latency_seconds (histogram)
  - End-to-end latency for recall.

- soma_eviction_index_size (gauge)
  - Number of items currently tracked in the eviction zset.

- soma_wal_pending_count (gauge)
  - Number of items pending in the WAL to be reconciled.

- soma_evictions_total (counter)
  - Number of evictions performed by the enforcer.

Example PromQL

- Store rate (Last 5m):
  rate(soma_store_total[5m])

- 99th percentile store latency (5m):
  histogram_quantile(0.99, rate(soma_store_latency_seconds_bucket[5m]))

- Eviction backlog alert (more than 10% of index):
  (soma_wal_pending_count / soma_eviction_index_size) > 0.1

Alerting suggestions

- High WAL backlog:
  - Trigger when `soma_wal_pending_count > 100` for 10 minutes.
- Eviction runaway:
  - Trigger when `rate(soma_evictions_total[5m]) > 10` for 5 minutes.
- Elevated store latency:
  - Trigger when `histogram_quantile(0.99, rate(soma_store_latency_seconds_bucket[5m])) > 1` (1s) for 5 minutes.
