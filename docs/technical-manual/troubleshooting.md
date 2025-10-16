---
title: "Troubleshooting Guide"
purpose: "Guide for diagnosing and resolving common issues"
audience: "System administrators and developers"
last_updated: "2025-10-16"
review_frequency: "monthly"
---

# Troubleshooting Guide

## Quick Reference

### Common Issues
| Issue | Symptoms | First Steps |
|-------|----------|-------------|
| High Latency | Slow responses | Check system resources |
| Memory Leaks | Growing memory usage | Monitor heap usage |
| Connection Errors | API timeouts | Check network connectivity |
| Data Inconsistency | Incorrect results | Verify cache consistency |

### Diagnostic Tools
1. Monitoring dashboards
2. Log aggregation
3. Profiling tools
4. Health checks

## System Health Checks

### API Service
```bash
# Check API health
curl http://localhost:9595/health

# Detailed health check
curl http://localhost:9595/health/detailed
```

### Component Status
```bash
# Vector store status
curl http://localhost:9595/health/vector

# Cache status
curl http://localhost:9595/health/cache

# Database status
curl http://localhost:9595/health/database
```

## Common Issues and Solutions

### 1. High Latency

#### Symptoms
- API response time > 200ms
- Query timeouts
- Client disconnections

#### Diagnosis
1. Check system metrics:
   ```bash
   # CPU usage
   top -bn1

   # Memory usage
   free -m

   # Disk I/O
   iostat -x 1
   ```

2. Monitor service metrics:
   ```bash
   curl http://localhost:9595/metrics
   ```

#### Solutions
1. **Resource Constraints**
   - Scale vertically
   - Add more nodes
   - Optimize queries

2. **Network Issues**
   - Check network latency
   - Verify DNS resolution
   - Monitor bandwidth usage

3. **Database Performance**
   - Review query plans
   - Update indexes
   - Optimize configurations

### 2. Memory Leaks

#### Symptoms
- Increasing memory usage
- OOM errors
- Performance degradation

#### Diagnosis
1. Monitor memory usage:
   ```bash
   # Memory trends
   ps aux | grep memory-service

   # Heap analysis
   pmap -x <pid>
   ```

2. Check service logs:
   ```bash
   tail -f /var/log/memory-service/service.log
   ```

#### Solutions
1. **Memory Management**
   - Adjust memory limits
   - Enable garbage collection
   - Monitor object lifecycle

2. **Resource Cleanup**
   - Clear cache
   - Close connections
   - Release resources

### 3. Connection Errors

#### Symptoms
- Connection timeouts
- Connection refused errors
- Network unreachable

#### Diagnosis
1. Check connectivity:
   ```bash
   # Network connectivity
   ping memory-service

   # Port availability
   nc -zv memory-service 9595
   ```

2. Verify configurations:
   ```bash
   # DNS resolution
   nslookup memory-service

   # Service discovery
   kubectl get endpoints
   ```

#### Solutions
1. **Network Issues**
   - Check firewall rules
   - Verify DNS settings
   - Review network policies

2. **Service Health**
   - Restart services
   - Check dependencies
   - Verify configurations

### 4. Data Inconsistency

#### Symptoms
- Incorrect query results
- Missing data
- Stale cache entries

#### Diagnosis
1. Verify data consistency:
   ```bash
   # Cache vs Database
   curl http://localhost:9595/debug/cache-stats

   # Vector store sync
   curl http://localhost:9595/debug/vector-sync
   ```

2. Check replication status:
   ```sql
   -- PostgreSQL replication lag
   SELECT * FROM pg_stat_replication;
   ```

#### Solutions
1. **Cache Issues**
   - Clear cache
   - Update TTL settings
   - Verify cache policy

2. **Data Sync**
   - Force reindexing
   - Check replication
   - Verify consistency

## Monitoring and Logging

### Log Analysis
```bash
# Error patterns
grep ERROR /var/log/memory-service/*.log

# Warning patterns
grep WARN /var/log/memory-service/*.log

# Specific error types
grep "ConnectionError" /var/log/memory-service/*.log
```

### Metrics Collection
```bash
# System metrics
curl http://localhost:9595/metrics

# Component metrics
curl http://localhost:9595/metrics/components
```

## Performance Analysis

### Query Performance
```sql
-- Slow query analysis
SELECT * FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

### Resource Usage
```bash
# CPU profiling
py-spy record -o profile.svg --pid <pid>

# Memory profiling
memory-profiler -o memory.prof <script>
```

## Recovery Procedures

### Service Recovery
1. **Restart Service**
   ```bash
   systemctl restart memory-service
   ```

2. **Clear Cache**
   ```bash
   redis-cli FLUSHALL
   ```

3. **Rebuild Indexes**
   ```bash
   curl -X POST http://localhost:9595/admin/rebuild-indexes
   ```

### Data Recovery
1. **Backup Restore**
   ```bash
   # Restore from backup
   pg_restore -d memory_db backup.sql

   # Verify restoration
   psql -c "SELECT count(*) FROM memories;"
   ```

2. **Vector Reindexing**
   ```bash
   # Rebuild vector index
   curl -X POST http://localhost:9595/admin/rebuild-vectors
   ```

## Preventive Measures

### Regular Maintenance
1. Log rotation
2. Index optimization
3. Cache cleanup
4. Resource monitoring

### Health Checks
1. Component status
2. Data consistency
3. Performance metrics
4. Resource usage

## Support Resources

### Documentation
- [Architecture Guide](architecture.md)
- [Performance Guide](performance.md)
- [Runbooks](runbooks/)

### Community
- GitHub Issues
- Discussion Forum
- Stack Overflow

### Enterprise Support
- 24/7 Support
- Priority Response
- Expert Consultation

## Further Reading
- [Monitoring Guide](monitoring.md)
- [Performance Tuning](performance.md)
- [Scaling Guide](scaling.md)
