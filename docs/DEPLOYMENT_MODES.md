# SomaFractalMemory Deployment Modes

This document explains the two deployment modes available for SomaFractalMemory and when to use each.

## Overview

SomaFractalMemory supports two distinct deployment approaches:

1. **App-Only Mode** - Deploy only application pods, connect to existing infrastructure
2. **Full Stack Mode** - Deploy application + infrastructure services together

## App-Only Mode (Production Recommended)

### When to Use
- Production environments with managed infrastructure
- Microservice architectures with shared infrastructure
- When Postgres, Redis, Kafka, and Qdrant are managed by ops teams
- Multi-tenant environments

### What Gets Deployed
- **API Pod**: HTTP FastAPI server (`somafractalmemory-runtime`)
- **Consumer Pod**: Background Kafka consumer (`somafractalmemory-runtime`)
- **Total**: 2 pods

### Infrastructure Dependencies
Must exist before deployment:
- **Postgres**: Database for memory storage
- **Redis**: Caching layer
- **Qdrant**: Vector database for embeddings
- **Kafka**: Message broker for events (optional if `EVENTING_ENABLED=false`)

### Deployment Commands
```bash
# Deploy only app pods
helm upgrade --install soma-memory ./helm \
  -n soma-memory \
  --create-namespace \
  --values helm/values-app-only.yaml \
  --set image.tag=v2.1.0 \
  --wait

# Verify deployment (should see 2 pods)
kubectl -n soma-memory get pods -l app.kubernetes.io/name=somafractalmemory
```

### Configuration
The `helm/values-app-only.yaml` file:
- Disables all infrastructure components (`postgres.enabled=false`, etc.)
- Points to external service endpoints
- Configures connection strings for shared infrastructure

## Full Stack Mode (Development Only)

### When to Use
- Local development environments
- Self-contained testing
- Demo environments
- When shared infrastructure doesn't exist

### What Gets Deployed
- **API Pod**: HTTP FastAPI server
- **Consumer Pod**: Background Kafka consumer
- **Postgres Pod**: Database service
- **Redis Pod**: Cache service
- **Qdrant Pod**: Vector database
- **Kafka Pod**: Message broker (optional)
- **Total**: 5-6 pods + PVCs

### Deployment Commands
```bash
# Deploy app + all infrastructure
helm upgrade --install soma-memory ./helm \
  -n soma-memory \
  --create-namespace \
  --values helm/values-dev-port9797.yaml \
  --set image.tag=local \
  --wait

# Verify deployment (should see 5-6 pods)
kubectl -n soma-memory get pods,pvc
```

### Configuration
The `helm/values-dev-port9797.yaml` file:
- Enables all infrastructure components
- Configures in-cluster service discovery
- Sets up development-friendly settings (no SSL, NodePort access)

## Key Differences

| Aspect | App-Only Mode | Full Stack Mode |
|--------|---------------|-----------------|
| **Pods Deployed** | 2 (API + Consumer) | 5-6 (App + Infrastructure) |
| **Infrastructure** | External/Managed | Self-Contained |
| **Production Ready** | ✅ Yes | ❌ No |
| **Resource Usage** | Low | High |
| **Complexity** | Simple | Complex |
| **Use Case** | Production | Development |

## Configuration Examples

### App-Only Configuration
```yaml
# helm/values-app-only.yaml
postgres:
  enabled: false
redis:
  enabled: false
qdrant:
  enabled: false

env:
  REDIS_HOST: "shared-redis.infra.svc.cluster.local"
  QDRANT_HOST: "shared-qdrant.infra.svc.cluster.local"

secret:
  data:
    POSTGRES_URL: "postgresql://user:pass@shared-postgres.infra.svc.cluster.local:5432/db"
```

### Full Stack Configuration
```yaml
# helm/values-dev-port9797.yaml
postgres:
  enabled: true
redis:
  enabled: true
qdrant:
  enabled: true

service:
  type: NodePort
  nodePort: 30797
```

## Migration Path

### From Full Stack to App-Only
1. Ensure shared infrastructure is available and accessible
2. Update connection strings in `helm/values-app-only.yaml`
3. Deploy using app-only values
4. Verify connectivity to shared services
5. Remove old full-stack deployment if needed

### From App-Only to Full Stack
1. Deploy using full-stack values
2. Wait for infrastructure pods to be ready
3. Application will automatically connect to local services

## Troubleshooting

### App-Only Issues
- **Connection refused**: Verify shared infrastructure endpoints are correct
- **DNS resolution**: Ensure namespace labels allow cross-namespace communication
- **Authentication**: Check credentials and SSL certificates for shared services

### Full Stack Issues
- **Resource limits**: Ensure cluster has enough CPU/memory for all pods
- **Storage**: Verify StorageClass is available for PVCs
- **Image pulls**: Check that all infrastructure images are accessible

## Best Practices

### Production
- Always use App-Only mode in production
- Separate infrastructure management from application deployment
- Use managed services (RDS, ElastiCache, etc.) when possible
- Implement proper secret management and rotation

### Development
- Use Full Stack mode for isolated development
- Consider shared development infrastructure for team environments
- Use persistent volumes to avoid data loss during pod restarts
- Monitor resource usage to prevent cluster overload
