# Database Service Runbook

## Overview

This runbook covers operational procedures for the PostgreSQL database service.

## Health Checks

### 1. Connection Check
```bash
# Check PostgreSQL connection
docker compose exec postgres psql -U soma -d somamemory -c 'SELECT 1;'

# Expected output:
 ?column?
----------
        1
```

### 2. Service Status
```bash
# Check service status
docker compose ps postgres
```

## Common Issues

### 1. Connection Failures

**Symptoms:**
- Connection refused
- Authentication failed
- Database doesn't exist

**Steps:**
```bash
# 1. Check PostgreSQL logs
docker compose logs postgres

# 2. Verify credentials
echo $POSTGRES_PASSWORD

# 3. Check database exists
docker compose exec postgres psql -U soma -l
```

### 2. Performance Issues

**Symptoms:**
- Slow queries
- High CPU usage
- High disk I/O

**Steps:**
```bash
# 1. Check active queries
docker compose exec postgres psql -U soma -d somamemory \
  -c 'SELECT * FROM pg_stat_activity WHERE state != \'idle\';'

# 2. View slow queries
docker compose exec postgres psql -U soma -d somamemory \
  -c 'SELECT * FROM pg_stat_activity ORDER BY duration DESC;'

# 3. Check table statistics
docker compose exec postgres psql -U soma -d somamemory \
  -c 'SELECT * FROM pg_stat_user_tables;'
```

### 3. Disk Space Issues

**Symptoms:**
- No space left on device
- Write failures

**Steps:**
```bash
# 1. Check disk usage
df -h /var/lib/postgresql/data

# 2. Find large tables
docker compose exec postgres psql -U soma -d somamemory -c \
  'SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||\'.\''||tablename)) AS size FROM pg_tables ORDER BY pg_total_relation_size(schemaname||\'.\''||tablename) DESC;'

# 3. Vacuum database
docker compose exec postgres psql -U soma -d somamemory -c 'VACUUM FULL;'
```

## Maintenance Tasks

### 1. Backup
```bash
# Full backup
docker compose exec postgres pg_dump -U soma somamemory > backup.sql

# Schema only
docker compose exec postgres pg_dump -U soma -s somamemory > schema.sql
```

### 2. Restore
```bash
# Stop service
docker compose stop postgres

# Restore from backup
cat backup.sql | docker compose exec -T postgres psql -U soma somamemory

# Start service
docker compose start postgres
```

### 3. Index Maintenance
```bash
# Reindex database
docker compose exec postgres psql -U soma -d somamemory -c 'REINDEX DATABASE somamemory;'

# Analyze tables
docker compose exec postgres psql -U soma -d somamemory -c 'ANALYZE VERBOSE;'
```

## Monitoring

### Key Metrics

| Metric | Warning | Critical | Action |
|--------|----------|-----------|--------|
| Connection Count | >80% max | >90% max | Scale up |
| Cache Hit Ratio | <90% | <80% | Increase cache |
| Disk Usage | >80% | >90% | Clean up |

### Useful Queries

```sql
-- Table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## Scaling

### Vertical Scaling
```bash
# Update resource limits
docker compose up -d postgres
```

### Connection Pooling
```bash
# Enable PgBouncer
docker compose -f docker-compose.yml -f docker-compose.pgbouncer.yml up -d
```

## Emergency Procedures

### Database Recovery
```bash
# 1. Stop writes
docker compose exec api curl -X POST /admin/readonly

# 2. Backup corrupted DB
docker compose exec postgres pg_dump -U soma somamemory > corrupt.sql

# 3. Restore from last good backup
cat backup.sql | docker compose exec -T postgres psql -U soma somamemory
```

### Data Corruption
```bash
# 1. Check table corruption
docker compose exec postgres psql -U soma -d somamemory \
  -c 'SELECT * FROM pg_stat_database;'

# 2. Repair tables
docker compose exec postgres psql -U soma -d somamemory \
  -c 'REINDEX DATABASE somamemory;'
```
