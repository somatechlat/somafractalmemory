# SomaFractalMemory Docker Deployment Guide

**Document ID**: SFM-DEPLOY-DOCKER-001
**Version**: 1.0.0
**Last Updated**: 2026-01-09
**Status**: Verified ✅

---

## 1. Overview

This guide provides step-by-step instructions for deploying SomaFractalMemory (SFM) using Docker Compose. SFM provides the hierarchical memory persistence layer for the SOMA cognitive architecture.

### 1.1 Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.0+ | 25.0+ |
| Docker Compose | v2.20+ | v2.24+ |
| RAM | 4GB | 8GB |
| Disk | 10GB | 20GB |
| CPU | 2 cores | 4 cores |

### 1.2 Architecture Overview

```
┌────────────────────────────────────────────────┐
│            SomaFractalMemory Stack             │
├────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐   │
│  │         SFM API (Django)                │   │
│  │           :10101                        │   │
│  └──────────────────┬──────────────────────┘   │
│                     │                           │
│  ┌──────────────────▼──────────────────────┐   │
│  │          Storage Layer                   │   │
│  │  PostgreSQL │ Redis │ Milvus            │   │
│  │   :25432    │:26379 │ :29530            │   │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

---

## 2. Quick Start (3 Minutes)

### Step 1: Navigate to Infrastructure Directory

```bash
cd /path/to/somafractalmemory/infra/docker
```

### Step 2: Start All Services

```bash
docker compose -p sfm up -d
```

### Step 3: Verify Deployment

```bash
# Check container status
docker compose -p sfm ps

# Verify health endpoint
curl http://localhost:10101/healthz
# Expected: {"kv_store": true, "vector_store": true, "graph_store": true}
```

---

## 3. Detailed Deployment Steps

### 3.1 Clone Repository

```bash
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory
git checkout SAAS-PRODUCTIONREADY
```

### 3.2 Build and Start Services

```bash
cd infra/docker

# Build images
docker compose -p sfm build

# Start all services
docker compose -p sfm up -d

# View logs
docker compose -p sfm logs -f sfm_api
```

### 3.3 Wait for Health Checks

```bash
# Wait for all services to be healthy
watch -n 5 'docker compose -p sfm ps'
```

---

## 4. Service Reference

### 4.1 Port Mapping

| Service | Host Port | Container Port | Purpose |
|---------|-----------|----------------|---------|
| sfm_api | 10101 | 10101 | Main API |
| postgres | 25432 | 5432 | Database |
| redis | 26379 | 6379 | Cache/KV |
| milvus | 29530 | 19530 | Vector store |

### 4.2 Default Configuration

```yaml
# API Configuration
SOMA_API_TOKEN: "dev-token-somastack2024"

# Database Configuration
SOMA_POSTGRES_URL: "postgres://somafractal:somafractal@sfm_postgres:5432/somafractal"
SOMA_REDIS_HOST: "sfm_redis"
SOMA_REDIS_PORT: "6379"
SOMA_MILVUS_HOST: "sfm_milvus"
SOMA_MILVUS_PORT: "19530"
```

---

## 5. API Endpoints

### 5.1 Health Check

```bash
curl http://localhost:10101/healthz
```

**Response:**
```json
{
  "kv_store": true,
  "vector_store": true,
  "graph_store": true
}
```

### 5.2 Memory Operations

```bash
# Store memory
curl -X POST http://localhost:10101/api/v1/memory \
  -H "Authorization: Bearer dev-token-somastack2024" \
  -H "Content-Type: application/json" \
  -d '{"key": "test", "value": {"content": "Hello"}, "namespace": "default"}'

# Recall memory
curl http://localhost:10101/api/v1/memory/test \
  -H "Authorization: Bearer dev-token-somastack2024"
```

---

## 6. E2E Verification

### 6.1 Run E2E Test

```bash
# From project root
cd /path/to/somafractalmemory

# Activate virtual environment
source .venv/bin/activate

# Run E2E test
python -m pytest tests/integration/test_end_to_end_memory.py -v
```

### 6.2 Expected Output

```
tests/integration/test_end_to_end_memory.py::test_save_and_retrieve_memory PASSED
```

---

## 7. Operations

### 7.1 Stopping Services

```bash
# Stop all services (preserve data)
docker compose -p sfm down

# Stop and remove volumes (DESTRUCTIVE)
docker compose -p sfm down -v
```

### 7.2 Viewing Logs

```bash
# All services
docker compose -p sfm logs -f

# Specific service
docker compose -p sfm logs -f sfm_api
```

---

## 8. Tilt Deployment (Development)

### Prerequisites

```bash
# Install Tilt
brew install tilt-dev/tap/tilt

# Start Minikube
minikube start --cpus=2 --memory=8g --profile sfm
```

### Deploy with Tilt

```bash
cd somafractalmemory

# Start Tilt
tilt up --port 10351

# Dashboard opens at http://localhost:10351
```

---

## 9. Kubernetes Deployment

### Deploy to K8s

```bash
cd somafractalmemory/infra/k8s

# Create namespace
kubectl create namespace sfm

# Apply manifests
kubectl apply -f . -n sfm

# Wait for pods
kubectl wait --for=condition=ready pod -l app=sfm-api -n sfm --timeout=180s

# Port forward for testing
kubectl port-forward svc/sfm-api 10101:10101 -n sfm
```

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| API returns 401 | Wrong token | Use `dev-token-somastack2024` |
| Database connection failed | Postgres not ready | Wait 30s and retry |
| Milvus connection refused | Container starting | Check `docker ps` for health |
| Migration error | Tables missing | Run `docker exec somafractalmemory_api python manage.py migrate` |

### 10.2 Reset Everything

```bash
docker compose -f infra/docker/docker-compose.yml --profile core down -v --remove-orphans
docker compose -f infra/docker/docker-compose.yml --profile core up -d
docker exec somafractalmemory_api python manage.py migrate
```

---

## Appendix: File Structure

```
infra/docker/
├── docker-compose.yml      # Main orchestration
├── Dockerfile              # Python app build
├── docker-entrypoint.sh    # Startup script
├── .dockerignore           # Build exclusions
├── README.md               # Quick reference
└── DEPLOYMENT_GUIDE.md     # This file
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0 | 2026-01-09 | Vibe Collective | Added Tilt, K8s, migrations |
| 1.0.0 | 2026-01-08 | Vibe Collective | Initial verified deployment |
