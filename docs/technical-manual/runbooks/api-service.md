# API Service Runbook

## Overview

This runbook covers common operational procedures for the Soma Fractal Memory API service.

## Health Checks

### 1. API Health
```bash
# Check API health endpoint
curl http://localhost:9595/healthz

# Expected output:
{"status": "healthy"}
```

### 2. Service Status
```bash
# Check service status
docker compose ps api
```

## Common Issues

### 1. API Not Responding

**Symptoms:**
- 502 Bad Gateway
- Connection refused
- Timeout errors

**Steps:**
```bash
# 1. Check logs
docker compose logs --tail=100 api

# 2. Restart service
docker compose restart api

# 3. Check metrics
curl http://localhost:9595/metrics
```

### 2. Authentication Failures

**Symptoms:**
- 401 Unauthorized
- 403 Forbidden

**Steps:**
```bash
# 1. Verify token
echo $SOMA_API_TOKEN

# 2. Check token file
cat /path/to/token/file

# 3. Reset token if needed
docker compose down
SOMA_API_TOKEN=newtoken docker compose up -d
```

### 3. High Latency

**Symptoms:**
- Slow response times
- Timeouts

**Steps:**
```bash
# 1. Check resource usage
docker stats api

# 2. View slow queries
docker compose exec postgres psql -U soma -d somamemory -c \
  'SELECT * FROM pg_stat_activity WHERE state != \'idle\' ORDER BY duration DESC;'

# 3. Check connection pool
curl http://localhost:9595/metrics | grep connections
```

## Maintenance Tasks

### 1. Log Rotation
```bash
# Check log size
du -h /var/log/containers/api*

# Rotate logs
docker compose exec api logrotate /etc/logrotate.d/api
```

### 2. Backup Configuration
```bash
# Backup config
cp config.yaml config.yaml.bak

# Restore config
cp config.yaml.bak config.yaml
```

### 3. Version Update
```bash
# Pull new image
docker compose pull api

# Update service
docker compose up -d api
```

## Monitoring

### Key Metrics

| Metric | Warning | Critical | Action |
|--------|----------|-----------|--------|
| API Latency | >200ms | >500ms | Check DB, cache |
| Error Rate | >1% | >5% | Check logs |
| Memory Usage | >80% | >90% | Scale up |

### Useful Queries

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Slow queries
SELECT * FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

## Scaling

### Horizontal Scaling
```bash
# Scale API instances
docker compose up -d --scale api=3
```

### Vertical Scaling
```bash
# Update resource limits
docker compose up -d --scale api=1 api
```

## Emergency Procedures

### Service Recovery
```bash
# 1. Stop service
docker compose stop api

# 2. Clear state
docker compose rm -f api

# 3. Start fresh
docker compose up -d api
```

### Data Recovery
```bash
# 1. Stop writes
docker compose exec api curl -X POST /admin/readonly

# 2. Backup data
docker compose exec postgres pg_dump -U soma somamemory > backup.sql

# 3. Restore service
docker compose restart api
```
