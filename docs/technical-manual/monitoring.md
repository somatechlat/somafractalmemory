# Monitoring Guide

## Overview

Soma Fractal Memory exposes metrics and health endpoints for comprehensive monitoring.

## Health Endpoints

### /healthz
Returns 200 OK when core services are healthy.

### /metrics
Exposes Prometheus metrics.

## Key Metrics

### Memory Operations
- `soma_memory_store_total` - Total store operations
- `soma_memory_recall_total` - Total recall operations
- `soma_memory_store_latency_seconds` - Store operation latency
- `soma_memory_recall_latency_seconds` - Recall operation latency

### Database Health
- PostgreSQL connections
- Redis cache hit rate
- Qdrant search latency

## Dashboards

### Grafana Dashboard Setup

1. Import the provided dashboard JSON:
   ```bash
   curl -X POST http://grafana:3000/api/dashboards/db \
     -H "Content-Type: application/json" \
     -d @dashboards/memory-metrics.json
   ```

2. Configure data sources:
   - Add Prometheus
   - Add PostgreSQL metrics
   - Add Redis metrics

## Alerts

### Critical Alerts
- Memory store failure rate > 1%
- Recall latency > 500ms
- Database connection failures

### Warning Alerts
- Memory store latency > 200ms
- Cache hit rate < 80%
- Available storage < 20%
