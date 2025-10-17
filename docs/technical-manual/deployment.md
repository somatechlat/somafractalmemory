---
title: Deployment Guide---
purpose: 'title: "Deployment Guide"'
audience:
- Operators and SREs
last_updated: '2025-10-16'
---


# Deployment Guide---

title: "Deployment Guide"

This guide describes the supported deployment paths for SomaFractalMemory. Each approach exposes the same `/memories` API.purpose: "Comprehensive instructions for deploying SomaFractalMemory in production"

audience: "DevOps engineers, SREs, system administrators"

## Docker Compose (Local / QA)last_updated: "2025-10-16"

review_frequency: "quarterly"

```bash---

cp .env.example .env

export SOMA_API_TOKEN=local-dev-token# Deployment Guide

export SOMA_RATE_LIMIT_MAX=120

export SOMA_RATE_LIMIT_WINDOW_SECONDS=60## Prerequisites



# Build images and start the stack- Kubernetes 1.20+ (or Docker Compose 2.0+)

make compose-up- Helm 3.0+

- kubectl configured with cluster access

# Verify readiness

curl http://localhost:9595/readyz## Port Strategy

curl -H "Authorization: Bearer ${SOMA_API_TOKEN}" http://localhost:9595/stats

```### SomaFractalMemory API



To stop the stack:| Environment | Public Port | Purpose | Notes |

|-------------|------------|---------|-------|

```bash| **Docker Compose** | 9595 | Public API Entry Point | Direct access, standard port |

make compose-down| **Kubernetes** | 9393 | Service Access (non-conflicting) | Internal Kubernetes port |

```

### Supporting Services (All Environments)

## Kubernetes (Helm)

| Service | Port | Purpose |

1. Configure secrets:|---------|------|---------|

| **PostgreSQL** | 40021 | Persistent memory storage |

   ```bash| **Redis** | 40022 | Hot cache layer |

   kubectl create secret generic somafractal-secrets \| **Qdrant Vector Store** | 40023 | Vector similarity search |

     --from-literal=SOMA_API_TOKEN=prod-token \| **Kafka** | 40024 | Event bus (optional) |

     --from-literal=SOMA_POSTGRES_URL=postgresql://user:pass@postgres:5432/soma

   ```## Docker Compose Deployment



2. Install the chart:### Environment Variables



   ```bash```bash

   helm install somafractalmemory ./helm -f helm/values-prod-ha.yamlexport API_PORT=9595               # PUBLIC API ENTRY POINT (default)

   ```export POSTGRES_HOST_PORT=40021

export REDIS_HOST_PORT=40022

3. Validate deployment:export QDRANT_HOST_PORT=40023

export KAFKA_INTERNAL_PORT=40024

   ```bash```

   kubectl get pods -l app.kubernetes.io/name=somafractalmemory

   kubectl port-forward svc/somafractalmemory 9595:9595### Startup

   curl -H "Authorization: Bearer prod-token" http://localhost:9595/health

   ``````bash

docker compose up -d

4. Configure ingress/mesh policies to expose `/memories`, `/stats`, `/health*`, and `/metrics` as required.```



## Configuration Reference### Verification



| Environment Variable | Purpose | Default |```bash

|----------------------|---------|---------|# Test API (9595 is the PUBLIC ENTRY POINT)

| `SOMA_API_TOKEN` | Token required for `/memories` routes. | _none_ |curl http://localhost:9595/health

| `SOMA_API_TOKEN_FILE` | Path to file containing the token. | _unset_ |

| `SOMA_RATE_LIMIT_MAX` | Requests allowed per window (global). | `60` |# Database (40021)

| `SOMA_RATE_LIMIT_WINDOW_SECONDS` | Rate limiter window length. | `60` |psql -h localhost -p 40021 -U soma -d somafractalmemory

| `SOMA_CORS_ORIGINS` | Comma-separated list of allowed origins. | _unset_ |

| `SOMA_MAX_REQUEST_BODY_MB` | Maximum request size. | `5` |# Cache (40022)

| `SOMA_MEMORY_NAMESPACE` | Logical namespace for stored payloads. | `api_ns` |redis-cli -p 40022 ping



## Post-Deployment Checklist# Vector Store (40023)

curl http://localhost:40023/health

- [ ] `/readyz` returns HTTP 200.

- [ ] `/metrics` is scraped by Prometheus.# Kafka (40024)

- [ ] `/stats` includes accurate `total_memories` counts during smoke tests.kafka-topics --bootstrap-server localhost:40024 --list

- [ ] Dashboards and alerts reference only the `/memories` latency histograms.```


## Kubernetes Deployment

### Port Configuration

All Kubernetes services use the 40020+ range with API on **port 9393**:

```bash
helm install somafractalmemory ./helm \
  -f ./helm/values-prod.yaml \
  -n memory
```

### Environment Variables (Kubernetes)

```yaml
POSTGRES_URL: "postgresql://soma:PASSWORD@somafractalmemory-postgres:40021/somafractalmemory"
REDIS_URL: "redis://somafractalmemory-redis:40022/0"
QDRANT_URL: "http://somafractalmemory-qdrant:40023"
KAFKA_BOOTSTRAP_SERVERS: "somafractalmemory-kafka:40024"
```

### Verification

```bash
# Port-forward to test API (9393)
kubectl port-forward svc/somafractalmemory-somafractalmemory 9393:9393 -n memory
curl http://localhost:9393/health

# Check service endpoints
kubectl get svc -n memory
```

## Configuration Reference

### Helm Values (values-local-dev.yaml)

```yaml
service:
  port: 9393  # Kubernetes API port (9393 for Kubernetes)

postgres:
  persistence:
    enabled: false

redis:
  persistence:
    enabled: false

qdrant:
  persistence:
    enabled: false

kafka:
  replicaCount: 1
```

### Docker Compose (docker-compose.yml)

```yaml
api:
  ports:
    - "9595:9595"  # Public API entry point
  command: ["uvicorn", "somafractalmemory.http_api:app", "--host", "0.0.0.0", "--port", "9595"]
```

## Post-Deployment Checks

### Docker Compose

```bash
# API Health (port 9595 - public entry point)
curl http://localhost:9595/health

# Database (40021)
psql -h localhost -p 40021 -U soma -d somafractalmemory

# Cache (40022)
redis-cli -p 40022 ping
```

### Kubernetes

```bash
# API Health (via port 9393)
kubectl port-forward svc/somafractalmemory-somafractalmemory 9393:9393 -n memory
curl http://localhost:9393/health

# Service status
kubectl get svc -n memory
```

## Troubleshooting

### Port Conflicts

- **Docker**: If port 40020 is in use, set `API_PORT=XXXX` environment variable
- **Kubernetes**: Port 9393 is reserved for Kubernetes. Adjust with `helm install --set service.port=XXXX`

### Connection Strings

Update your client configuration based on deployment:

**Docker**:
```
API: http://localhost:9595
Database: postgresql://localhost:40021
Cache: redis://localhost:40022
```

**Kubernetes**:
```
API: http://somafractalmemory:9393 (from within cluster)
Database: postgresql://somafractalmemory-postgres:40021
Cache: redis://somafractalmemory-redis:40022
```

## Further Reading
- [Monitoring Guide](monitoring.md)
- [Architecture Guide](architecture.md)



### Resource Requirements

| Component | CPU | Memory | Storage |
|-----------|-----|---------|----------|
| API | 1-2 cores | 2-4GB | - |
| PostgreSQL | 2-4 cores | 4-8GB | 100GB |
| Redis | 1-2 cores | 2-4GB | 20GB |
| Qdrant | 2-4 cores | 4-8GB | 50GB |

## Monitoring Setup

```bash
# Install monitoring stack
helm install prometheus prometheus-community/kube-prometheus-stack

# Configure Grafana
kubectl apply -f monitoring/
```

## Security Considerations

1. Set strong passwords
2. Enable TLS
3. Configure network policies
4. Set up RBAC

## Scaling Guidelines

### Horizontal Scaling

```bash
# Scale API pods
kubectl scale deployment memory-api --replicas=3

# Scale Redis cluster
helm upgrade memory soma/somafractalmemory --set redis.replicas=3
```

## Verification

```bash
# Check pod status
kubectl get pods

# Test API health
curl https://api.example.com/healthz

# View logs
kubectl logs -l app=memory-api
```

## Rollback Procedure

```bash
# List Helm revisions
helm history memory

# Rollback to previous version
helm rollback memory 1
```
