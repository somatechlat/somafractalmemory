# Monitoring and Observability

## Overview

Comprehensive monitoring ensures SomaFractalMemory operates reliably across all service components in the 40020 port range.

## Service Health Endpoints

### API Service (Port 40020)

```bash
# Overall health
curl http://localhost:40020/health

# Detailed component health
curl http://localhost:9595/health/detailed
```

### Component Checks

```bash
# PostgreSQL (Port 40021)
pg_isready -h localhost -p 40021 -U soma

# Redis (Port 40022)
redis-cli -p 40022 ping

# Qdrant (Port 40023)
curl http://localhost:40023/health

# Kafka (Port 40024)
kafka-topics --bootstrap-server localhost:40024 --list
```

## Key Metrics

### API Metrics (Port 40020)

```bash
curl http://localhost:9595/metrics
```

Key indicators:
- Request latency (p50, p95, p99)
- Error rates
- Throughput (requests/sec)
- soma_memory_store_total
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
- [Troubleshooting Guide](troubleshooting.md)
- [Scaling Guide](scaling.md)
- Memory store latency > 200ms
- Cache hit rate < 80%
- Available storage < 20%
