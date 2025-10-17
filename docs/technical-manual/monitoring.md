---
title: "Monitoring & Observability# Monitoring and Observability"
purpose: "Monitoring focuses on the `/memories` request path and the public operational probes.## Overview"
audience:
  - "Operators and SREs"
last_updated: "2025-10-16"
---

# Monitoring & Observability# Monitoring and Observability



Monitoring focuses on the `/memories` request path and the public operational probes.## Overview



## MetricsComprehensive monitoring ensures SomaFractalMemory operates reliably across all service components in the 40020 port range.



The FastAPI service exposes Prometheus metrics at `/metrics`. Key series:## Service Health Endpoints



| Metric | Labels | Description |### API Service (Port 40020)

|--------|--------|-------------|

| `api_requests_total` | `endpoint`, `method` | Request volume per route. Use it to confirm only `/memories` surfaces receive authenticated traffic. |```bash

| `api_request_latency_seconds` | `endpoint`, `method` | Request latency histogram. Track `p95` latency for `POST /memories` and `POST /memories/search`. |# Overall health

| `api_responses_total` | `endpoint`, `method`, `status` | Response status distribution. Alerts fire when 5xx for `/memories*` exceed 1% of traffic. |curl http://localhost:40020/health

| `soma_memory_store_total` | `namespace` | Total store calls executed by the core layer. |

| `soma_memory_recall_total` | `namespace` | Total hybrid recall calls executed. |# Detailed component health

curl http://localhost:9595/health/detailed

## Dashboards```



1. **API Health**: display request rate, latency, and error ratio for `POST /memories`, `GET /memories/{coord}`, `POST /memories/search`.### Component Checks

2. **Backend Dependencies**: monitor Postgres connections, Qdrant availability, and Redis latency (if enabled).

3. **Rate Limiter Saturation**: chart remaining capacity derived from `429` responses.```bash

# PostgreSQL (Port 40021)

## Alertspg_isready -h localhost -p 40021 -U soma



| Alert | Condition | Response |# Redis (Port 40022)

|-------|-----------|----------|redis-cli -p 40022 ping

| `SOMAApiHighErrorRate` | `sum(rate(api_responses_total{status="500", endpoint=~"/memories.*"}[5m])) / sum(rate(api_requests_total{endpoint=~"/memories.*"}[5m])) > 0.02` for 10 minutes | Page the on-call SRE, run the [API service runbook](runbooks/api-service.md). |

| `SOMANoSearchTraffic` | `sum(rate(api_requests_total{endpoint="/memories/search", method="POST"}[1h])) == 0` | Investigate upstream clients—search traffic should always be non-zero after business hours. |# Qdrant (Port 40023)

| `SOMARedisUnavailable` | Redis ping failure longer than 5 minutes | The API falls back to in-memory rate limiting; review scaling requirements. |curl http://localhost:40023/health



## Tracing# Kafka (Port 40024)

kafka-topics --bootstrap-server localhost:40024 --list

OpenTelemetry tracing is enabled via `configure_tracer` when available. The recommended configuration exports spans to the platform collector with the service name `somafractalmemory-api`. Each `/memories` request produces a span with:```



- Attributes: `http.method`, `http.route`, `auth.authenticated` (bool), `client.namespace` (if header set).## Key Metrics

- Events: rate limit checks and vector store latency measurements.

### API Metrics (Port 40020)

## Logging

```bash

Structured JSON logs are emitted with the following keys:curl http://localhost:9595/metrics

```

- `event`: `request.start`, `request.finish`, `memory.store`, `memory.search`.

- `path`: request path.Key indicators:

- `status_code`: HTTP status.- Request latency (p50, p95, p99)

- `duration_ms`: request duration.- Error rates

- Throughput (requests/sec)

Ship logs to the central ELK stack and set retention to 7 days for privacy compliance.- soma_memory_store_total

- soma_memory_recall_total

### Database Metrics (Port 40021)

- PostgreSQL connections
- Query execution time
- Cache hit ratio
- Replication lag

### Cache Metrics (Port 40022)

- Redis hit/miss ratio
- Eviction rate
- Memory utilization

### Vector Store Metrics (Port 40023)

- Search latency (qdrant_search_latency_seconds)
- Index size
- Query distribution

### Kafka Metrics (Port 40024)

- Consumer lag
- Throughput
- Broker health

## Dashboards

### Grafana Setup

```bash
# Port-forward Grafana (if deployed)
kubectl port-forward svc/grafana 3000:3000

# Access at http://localhost:3000
```

### Import Dashboards

```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboards/memory-metrics.json
```

### Key Dashboards

1. **SomaFractalMemory Overview**
   - API latency and error rates
   - Service dependencies
   - Resource utilization

2. **Database Performance** (PostgreSQL 40021)
   - Active connections
   - Query execution time
   - Transaction rates

3. **Cache Efficiency** (Redis 40022)
   - Hit rate
   - Memory usage
   - Eviction patterns

4. **Vector Operations** (Qdrant 40023)
   - Search latency
   - Index health
   - Query volume

5. **Message Queue** (Kafka 40024)
   - Consumer lag
   - Throughput
   - Topic metrics

## Alerts

### Critical Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| API Down | Health check fails (40020) | CRITICAL | Page on-call immediately |
| High Latency | p99 > 500ms | WARNING | Investigate resource usage |
| PostgreSQL Down | Connection fails (40021) | CRITICAL | Initiate failover |
| Redis Down | Connection fails (40022) | WARNING | Manual recovery |
| Qdrant Down | Health fails (40023) | CRITICAL | Investigate vector store |
| Kafka Down | Broker unavailable (40024) | WARNING | Check cluster status |
| Memory Store Failure | Error rate > 1% | WARNING | Review logs |
| Recall Latency | > 500ms | WARNING | Check query patterns |

## Logging

### Log Aggregation

All services log to stdout:

```bash
# Kubernetes logs
kubectl logs -f deployment/somafractalmemory-somafractalmemory -n memory

# Docker Compose logs
docker compose logs -f api
```

### Log Levels

- ERROR: Critical failures
- WARN: Degraded operation
- INFO: Normal operations
- DEBUG: Detailed troubleshooting

### Log Format

All logs include:
- Timestamp (ISO 8601)
- Service name
- Log level
- Message
- Trace ID (for distributed tracing)

## OpenTelemetry Integration

### Tracing

```bash
# Export to Jaeger (if deployed)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### Metrics Collection

Prometheus scrapes metrics from `/metrics` endpoint on port 40020.

## Further Reading
- [Deployment Guide](deployment.md)
- Memory store latency > 200ms
- Cache hit rate < 80%
- Available storage < 20%
