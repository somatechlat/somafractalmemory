# Troubleshooting Guide

## Common Issues

### 1. Environment Setup

#### Docker Issues

**Problem**: Services won't start
```bash
# Check status
docker compose ps

# View logs
docker compose logs

# Solution
docker compose down -v
docker compose up -d
```

#### Python Issues

**Problem**: Package conflicts
```bash
# Check environment
pip list

# Solution
rm -rf .venv
python -m venv .venv
pip install -r api-requirements.txt
```

#### Database Issues

**Problem**: Connection errors
```bash
# Check connection
docker compose exec postgres pg_isready

# View logs
docker compose logs postgres

# Solution
docker compose restart postgres
```

### 2. Development Issues

#### Test Failures

**Problem**: Tests failing
```bash
# Run specific test
pytest tests/test_core.py -v

# Debug test
pytest tests/test_core.py -vv --pdb

# Check coverage
pytest --cov=somafractalmemory tests/
```

#### Code Style

**Problem**: Linting errors
```bash
# Format code
black somafractalmemory/

# Check style
flake8 somafractalmemory/

# Type check
mypy somafractalmemory/
```

#### Git Issues

**Problem**: Merge conflicts
```bash
# Update main
git fetch upstream
git rebase upstream/main

# Check status
git status

# Resolve conflicts
git add .
git rebase --continue
```

### 3. Runtime Issues

#### Performance

**Problem**: High latency
```bash
# Check metrics
curl http://localhost:9595/metrics

# Monitor resources
docker stats

# Profile code
python -m cProfile script.py
```

#### Memory Usage

**Problem**: Out of memory
```bash
# Check memory
docker stats

# Clear cache
docker compose exec redis redis-cli FLUSHALL

# Restart service
docker compose restart api
```

#### Connection Issues

**Problem**: Service unreachable
```bash
# Check health
curl http://localhost:9595/healthz

# View logs
docker compose logs api

# Restart service
docker compose restart api
```

## Debugging Tools

### 1. Logging

#### Enable Debug Logs
```bash
# Set level
export SOMA_LOG_LEVEL=DEBUG

# View logs
docker compose logs -f api

# Filter logs
docker compose logs | grep ERROR
```

### 2. Monitoring

#### Check Metrics
```bash
# System metrics
curl http://localhost:9595/metrics

# Custom metrics
curl http://localhost:9595/metrics/custom

# Health check
curl http://localhost:9595/healthz
```

### 3. Profiling

#### CPU Profile
```bash
# Run profiler
python -m cProfile -o output.prof script.py

# Analyze results
python -m pstats output.prof

# Visualize
snakeviz output.prof
```

## Recovery Procedures

### 1. Data Recovery

#### Backup Restore
```bash
# Stop services
docker compose down

# Restore backup
cat backup.sql | docker compose exec -T postgres psql -U soma

# Start services
docker compose up -d
```

### 2. Service Recovery

#### Reset State
```bash
# Stop services
docker compose down

# Clear volumes
docker compose down -v

# Fresh start
docker compose up -d
```

### 3. Index Recovery

#### Rebuild Index
```bash
# Check status
curl http://localhost:9595/admin/index/status

# Rebuild index
curl -X POST http://localhost:9595/admin/index/rebuild

# Monitor progress
curl http://localhost:9595/admin/index/progress
```

## Prevention Tips

### 1. Development

#### Best Practices
- Run tests locally
- Use pre-commit hooks
- Review changes
- Keep dependencies updated

### 2. Deployment

#### Checklist
- Backup data
- Check resources
- Test rollback
- Monitor metrics

### 3. Maintenance

#### Regular Tasks
- Update dependencies
- Clean old data
- Check logs
- Monitor performance

## Getting Help

### 1. Resources

- Documentation
- GitHub Issues
- Stack Overflow
- Team chat

### 2. Contact

- Team: #team-soma-memory
- Email: support@somatechlat.com
- Emergency: on-call@somatechlat.com

### 3. Escalation

1. Team member
2. Tech lead
3. Engineering manager
4. CTO
