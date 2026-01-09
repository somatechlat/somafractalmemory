# SomaFractalMemory Kubernetes Deployment (Tilt)

## Overview
Storage tier (L2) for the SOMA Stack. Contains K8s manifests for local development using Tilt + Minikube.

## Prerequisites
- Minikube with `vfkit` driver (macOS)
- Tilt v0.33+
- kubectl configured for `sfm` context
- 8GB RAM minimum for VM

## Quick Start
```bash
# Start Minikube profile
minikube start -p sfm --driver=vfkit --memory=8192 --cpus=4

# Configure Docker environment
eval $(minikube docker-env -p sfm)

# Start Tilt
tilt up --port 10353
```

## Architecture
```
sfm-resilient.yaml
├── Namespace: sfm
├── ConfigMap (sfm-config)
├── Deployments
│   ├── postgres (15-alpine)
│   ├── redis (7-alpine)
│   ├── milvus (v2.3.4)
│   └── sfm-api
├── Services
│   ├── postgres:5432
│   ├── redis:6379
│   ├── milvus:19530
│   └── sfm-api:10101 (NodePort 30101)
├── PVCs
│   ├── pgdata (2Gi)
│   ├── redis-data (1Gi)
│   └── milvus-data (4Gi)
└── Job (sfm-migrations)
```

## Resource Limits

| Component | Memory Req | Memory Limit | CPU Req | CPU Limit |
|-----------|------------|--------------|---------|-----------|
| sfm-api | 128Mi | 384Mi | 50m | 4000m |
| postgres | 256Mi | 512Mi | 50m | 4000m |
| redis | 64Mi | 256Mi | 25m | 4000m |
| milvus | 512Mi | 2Gi | 100m | 4000m |

## Environment Variables (ConfigMap)
```yaml
DJANGO_ENV: "production"
DJANGO_SETTINGS_MODULE: "somafractalmemory.settings"
SOMA_API_PORT: "10101"
SOMA_DB_NAME: "somamemory"
SOMA_POSTGRES_URL: "postgresql://soma:soma@postgres:5432/somamemory"
SOMA_REDIS_HOST: "redis"
SOMA_REDIS_PORT: "6379"
SOMA_MILVUS_HOST: "milvus"
SOMA_MILVUS_PORT: "19530"
SOMA_API_TOKEN: "dev-token-somastack2024"
ALLOWED_HOSTS: "*"
```

## Port Forwards
| Service | Host Port | Container Port |
|---------|-----------|----------------|
| sfm-api | 10101 | 10101 |
| postgres | 30201 | 5432 |
| redis | 30202 | 6379 |
| milvus | 30203 | 19530 |

## Commands

```bash
# Start Tilt dashboard
tilt up --port 10353

# Apply manifests manually
kubectl apply -f sfm-resilient.yaml -n sfm

# Check pod status
kubectl get pods -n sfm

# View API logs
kubectl logs -f deployment/sfm-api -n sfm

# Run migrations manually
kubectl exec -it deployment/sfm-api -n sfm -- python manage.py migrate

# Port-forward API
kubectl port-forward svc/sfm-api 10101:10101 -n sfm
```

## Health Check
```bash
curl http://localhost:10101/healthz
```

## Troubleshooting

### Pods stuck in Init
Check init container logs:
```bash
kubectl logs -f deployment/sfm-api -n sfm -c wait-for-postgres
```

### Milvus crashes
Milvus requires 2Gi minimum. Ensure VM has 8GB+ RAM.

### Database connection errors
Verify postgres pod is healthy:
```bash
kubectl exec -it deployment/postgres -n sfm -- pg_isready -U soma
```
