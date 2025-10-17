---
title: "Monitoring & Observability"
purpose: "Define the health, logging, and alerting standards for SomaFractalMemory."
audience:
  - "Operators"
  - "SREs"
last_updated: "2025-10-17"
review_frequency: "quarterly"
---

# Monitoring & Observability

Comprehensive monitoring ensures SomaFractalMemory remains healthy across its API, PostgreSQL, Redis, and Qdrant components. All references below assume the unified port map: API **9595**, Postgres **40021→5432**, Redis **40022→6379**, Qdrant **40023→6333**.

## Metrics

The FastAPI service exposes Prometheus metrics at `http://<api-host>:9595/metrics`.

| Metric | Labels | Description |
|--------|--------|-------------|
| `api_requests_total` | `endpoint`, `method` | Request volume per route. Use it to confirm authenticated traffic hits `/memories*` routes. |
| `api_request_latency_seconds` | `endpoint`, `method` | Histogram of request latency; track `p95` for `POST /memories` and `POST /memories/search`. |
| `api_responses_total` | `endpoint`, `method`, `status` | Response distribution; trigger alerts when 5xx exceed 2% of `/memories*` traffic. |
| `soma_memory_store_total` | `namespace` | Total successful store operations. |
| `soma_memory_recall_total` | `namespace` | Total hybrid recall executions. |

### Component Metrics
- **PostgreSQL (`40021` service / `5432` container)**: connection saturation, transaction latency, replication lag.
- **Redis (`40022` / `6379`)**: hit ratio, eviction rate, memory utilization.
- **Qdrant (`40023` / `6333`)**: search latency (`qdrant_search_latency_seconds`), index size, collection load.

## Health Checks

```bash
# API
curl http://localhost:9595/healthz
curl http://localhost:9595/readyz

# Postgres
pg_isready -h localhost -p 40021 -U soma

# Redis
redis-cli -p 40022 ping

# Qdrant
curl http://localhost:40023/healthz
```

For Kubernetes clusters, port-forward the respective services (`kubectl port-forward svc/<service> <local>:<service-port>`).

## Dashboards

Recommended Grafana dashboards:
1. **API Overview** – latency, throughput, and error rates for `/memories*` endpoints.
2. **Storage & Cache** – PostgreSQL connections, Qdrant latency, Redis hit/miss ratio.
3. **Rate Limiter** – 429 frequency, Redis saturation, token bucket utilisation.

## Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| API Down | `curl /healthz` fails twice in 30s | CRITICAL | Page on-call, follow [API service runbook](runbooks/api-service.md). |
| High API Error Rate | `5xx > 2%` over 5m for `/memories*` | WARNING | Inspect recent deploys and Redis/Qdrant health. |
| Postgres Unavailable | `pg_isready` failure > 1m | CRITICAL | Fail over or restore database. |
| Redis Unavailable | `redis-cli ping` failure > 5m | WARNING | Investigate resource pressure; rate limiting will degrade. |
| Qdrant Latency | `p99 > 250ms` for `qdrant_search_latency_seconds` | WARNING | Review index/load configuration. |

## Logging

- Structured JSON logs include `timestamp`, `service`, `path`, `status_code`, `duration_ms`, and trace identifiers.
- Collect with `docker compose logs -f api` locally or `kubectl logs -f deployment/<release>-somafractalmemory` in Kubernetes.
- Retain seven days in centralized storage to meet privacy policies.

## Tracing

If OpenTelemetry is enabled, set `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME=somafractalmemory-api`. Each `/memories` request emits spans covering rate limiter checks, Postgres writes, and Qdrant searches.

## Further Reading
- [Deployment Guide](deployment.md)
- [Runbooks](runbooks/)
- [Security Policy](security/secrets-policy.md)
