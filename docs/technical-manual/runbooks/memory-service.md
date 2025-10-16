---
title: "Memory Service Runbook"
purpose: "Operational procedures for the core memory service"
audience: "SRE and DevOps teams"
last_updated: "2025-10-16"
review_frequency: "monthly"
---

# Memory Service Runbook

## Service Overview
The memory service is the core component of SomaFractalMemory, responsible for storing and retrieving memories using a hybrid storage system.

## Key Components
- PostgreSQL database (primary storage)
- Redis cache
- Qdrant vector store
- Optional Kafka event bus

## Health Checks
1. API Health: `curl http://localhost:9595/health`
2. Vector Store: `curl http://localhost:9595/health/vector`
3. Cache Status: `curl http://localhost:9595/health/cache`

## Common Issues

### High Memory Usage
**Symptoms:**
- Memory usage > 85%
- Increased latency in vector operations

**Resolution:**
1. Check Redis memory usage: `redis-cli INFO memory`
2. Consider scaling horizontally if persistent
3. Review cache eviction policies

### Slow Vector Queries
**Symptoms:**
- Vector similarity search taking > 500ms
- High CPU usage in Qdrant pods

**Resolution:**
1. Check Qdrant metrics
2. Consider index optimization
3. Scale vector store resources

## Maintenance Tasks

### Backup Procedures
1. Database backup: `pg_dump -U postgres somafractal > backup.sql`
2. Vector store snapshot: See [Qdrant Backup Guide](../backup-and-recovery.md)

### Cache Management
1. Monitor hit rates: `redis-cli INFO stats`
2. Clear cache if needed: `redis-cli FLUSHDB`

## Monitoring

### Key Metrics
- Request latency (p95, p99)
- Cache hit ratio
- Vector store query time
- Memory usage per component

### Dashboards
- Memory Service Overview: `http://grafana:3000/d/memory-service`
- Vector Store Performance: `http://grafana:3000/d/vector-metrics`

## Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| HighMemoryUsage | > 85% | Check cache, consider scaling |
| SlowVectorQueries | p95 > 500ms | Optimize indexes, check load |
| CacheHitRateLow | < 60% | Review caching strategy |

## Contact Information

- Primary oncall: `#memory-service-oncall`
- Escalation: `#sre-escalation`
- Documentation: [Technical Manual](../index.md)
