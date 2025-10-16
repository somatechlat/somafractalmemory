# SomaFractalMemory Port Strategy

**Last Updated**: October 16, 2025

## Executive Summary

Port **9595** is the **PUBLIC API ENTRY POINT** for all deployments. This is where external clients connect.

---

## Port Configuration by Environment

### 🐳 Docker Compose (Local Development)

```
PUBLIC API ENTRY POINT: http://localhost:9595
```

| Service | Host Port | Container Port | Purpose |
|---------|-----------|-----------------|---------|
| **API** | 9595 | 9595 | **PUBLIC ENTRY POINT** |
| **PostgreSQL** | 40021 | 5432 | Persistent storage |
| **Redis** | 40022 | 6379 | Cache layer |
| **Qdrant** | 40023 | 6333 | Vector similarity search |
| **Kafka** | 40024 | 9092 | Event bus |

**Environment Variables:**
```bash
export API_PORT=9595               # PUBLIC (default: 9595)
export POSTGRES_HOST_PORT=40021
export REDIS_HOST_PORT=40022
export QDRANT_HOST_PORT=40023
export KAFKA_INTERNAL_PORT=40024
```

**Connection Examples:**
```bash
# API - PUBLIC ENTRY POINT
curl http://localhost:9595/health

# Database
psql -h localhost -p 40021 -U soma -d somafractalmemory

# Cache
redis-cli -p 40022 ping

# Vector Store
curl http://localhost:40023/health
```

---

### ☸️ Kubernetes (Production)

```
PUBLIC API ENTRY POINT: http://somafractalmemory:9393 (from within cluster)
SERVICE ACCESS: kubectl port-forward svc/somafractalmemory-somafractalmemory 9393:9393
```

| Service | Container Port | Service Port | Internal Connection |
|---------|-----------------|------|---|
| **API** | 9393 | 9393 | `http://somafractalmemory:9393` |
| **PostgreSQL** | 5432 | 40021 | `postgresql://postgres:40021` |
| **Redis** | 6379 | 40022 | `redis://redis:40022` |
| **Qdrant** | 6333 | 40023 | `http://qdrant:40023` |
| **Kafka** | 9092 | 40024 | `kafka:40024` |

**Connection Examples:**
```bash
# API - PORT FORWARD FOR TESTING
kubectl port-forward svc/somafractalmemory-somafractalmemory 9393:9393 -n memory
curl http://localhost:9393/health

# From within cluster
curl http://somafractalmemory:9393/health
```

---

## Key Design Decisions

### Why Port 9595?

1. **Standard Convention**: 9xxx range is reserved for application services
2. **Public Entry Point**: Directly exposed, no mapping needed
3. **Consistency**: Same across all documentation and examples
4. **Simplicity**: Easy to remember and configure

### Why Different Ports for Kubernetes (9393)?

1. **Conflict Avoidance**: Prevents port collision with other services
2. **Standards Alignment**: Follows Kubernetes conventions
3. **Security**: Isolates public and internal ports
4. **Flexibility**: Allows running multiple API versions simultaneously

### Supporting Services (40021-40024)

1. **High Port Range**: 40000+ is less likely to conflict
2. **Predictable**: Sequential numbering for easy management
3. **Documentation**: Easy to identify as "support services"
4. **Consistency**: Same across Docker and Kubernetes

---

## Client Connection Guide

### For Docker Compose Users

```bash
# Always use port 9595
curl http://localhost:9595/api/v1/memory/store \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Your memory"}'
```

### For Kubernetes Users (From Within Cluster)

```bash
# Use service name and port 9393
curl http://somafractalmemory:9393/api/v1/memory/store \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Your memory"}'
```

### For Kubernetes Users (From External Host)

```bash
# Port-forward first
kubectl port-forward svc/somafractalmemory-somafractalmemory 9393:9393 -n memory

# Then connect via localhost:9393
curl http://localhost:9393/api/v1/memory/store \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Your memory"}'
```

---

## Configuration Files

### docker-compose.yml
```yaml
ports:
  - "${API_PORT:-9595}:9595"  # PUBLIC ENTRY POINT
```

### helm/values-local-dev.yaml
```yaml
service:
  port: 9393  # Kubernetes service port
```

### helm/templates/service.yaml
```yaml
targetPort: 9393
port: {{ .Values.service.port }}
```

### helm/templates/deployment.yaml
```yaml
containerPort: 9393
```

---

## Verification Checklist

- ✅ Docker Compose API: `curl http://localhost:9595/health`
- ✅ Kubernetes API: `kubectl port-forward svc/somafractalmemory-somafractalmemory 9393:9393`
- ✅ Support services on 40021-40024 range
- ✅ All documentation references 9595 (Docker) and 9393 (Kubernetes)
- ✅ Health checks configured correctly
- ✅ Connection strings point to correct ports

---

## Migration Guide (If Updating From Older Versions)

If updating from version using port mapping (40020:9595):

1. **Update docker-compose.yml**: Change port mapping from `40020:9595` to `9595:9595`
2. **Update connection strings**: Change from `localhost:40020` to `localhost:9595`
3. **Update firewall rules**: Open port 9595 instead of 40020
4. **Update documentation**: All examples now use 9595 as primary port
5. **Update Helm deployments**: Kubernetes already uses 9393 (no change needed)

---

## References

- [Deployment Guide](docs/technical-manual/deployment.md)
- [Quick Start Tutorial](docs/user-manual/quick-start-tutorial.md)
- [Installation Guide](docs/user-manual/installation.md)
- [Troubleshooting Guide](docs/technical-manual/troubleshooting.md)
