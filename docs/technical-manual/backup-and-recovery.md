# Backup and Recovery Guide

## Overview

This guide covers backup procedures and disaster recovery for Soma Fractal Memory.

## Components to Backup

### 1. PostgreSQL Data
```bash
# Backup PostgreSQL database
docker compose exec postgres pg_dump -U soma somamemory > backup.sql

# Restore PostgreSQL database
cat backup.sql | docker compose exec -T postgres psql -U soma somamemory
```

### 2. Redis Data
```bash
# Backup Redis
docker compose exec redis redis-cli SAVE

# Copy dump.rdb
docker cp somafractalmemory_redis:/data/dump.rdb ./redis-backup.rdb
```

### 3. Qdrant Vectors
```bash
# Backup Qdrant collections
docker compose exec qdrant qdrant-backup /qdrant/storage backup.tar.gz
```

## Backup Schedule

| Component | Frequency | Retention |
|-----------|-----------|------------|
| PostgreSQL | Daily | 30 days |
| Redis | Hourly | 7 days |
| Qdrant | Daily | 30 days |

## Disaster Recovery

### Complete System Recovery

1. Stop all services:
   ```bash
   docker compose down
   ```

2. Restore data:
   ```bash
   # Restore PostgreSQL
   cat backup.sql | docker compose exec -T postgres psql -U soma somamemory

   # Restore Redis
   docker cp redis-backup.rdb somafractalmemory_redis:/data/dump.rdb

   # Restore Qdrant
   docker compose exec qdrant qdrant-restore /qdrant/storage backup.tar.gz
   ```

3. Restart services:
   ```bash
   docker compose up -d
   ```

### Verification

After recovery, verify:
1. API health endpoint
2. Sample memory retrieval
3. Metrics and monitoring
