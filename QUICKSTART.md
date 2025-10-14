# SomaFractalMemory - Quick Start

## 🚀 Automatic Docker Deployment (Recommended)

### One-Command Evented Enterprise Stack:
```bash
./scripts/assign_ports_and_start.sh
# OR
make setup-dev
```

This script will:
- ✅ **Automatically detect and resolve port conflicts**
- ✅ Assign free ports to all infrastructure services
- ✅ Start complete evented enterprise stack (API + Consumer + PostgreSQL + Redis + Qdrant + Kafka)
- ✅ Display final port assignments
- ✅ Ensure **zero conflicts** with existing services

### Server Access:
- **Memory API**: http://localhost:9595 (fixed)
- **Health**: http://localhost:9595/healthz
- **Stats**: http://localhost:9595/stats
- **API Docs**: http://localhost:9595/docs
- **Infrastructure ports**: Auto-assigned (displayed at startup)

### Manual Docker Commands:
```bash
# Check running containers
docker ps | grep somafractalmemory

# View current port assignments
cat .env

# Stop all services
docker compose --profile core down

# Quick test
curl http://localhost:9595/healthz
```

## 🎯 **Just run `./scripts/assign_ports_and_start.sh` and get a complete zero-conflict deployment!**

## 🔧 Kubernetes Deployment (Alternative)

### Auto Server Startup:
```bash
./scripts/auto-server.sh
```

This will set up Kubernetes port forwarding for development.

### Manual K8s Commands:
```bash
# Check pods
kubectl get pods -l app.kubernetes.io/instance=soma-memory

# Manual port forward
kubectl port-forward <pod-name> 9595:9595
```

## Async gRPC server (developer quick-run)

The repository contains an asyncio gRPC server useful for integration testing
against the real infra (Redis, Postgres, Qdrant). To run it locally:

```bash
# start required infra
docker compose up -d postgres qdrant redis

# activate venv and run server (background)
source .venv/bin/activate
python -m somafractalmemory.async_grpc_server &

# run the small client script which calls Health → Store → Recall → Delete
# see docs/CANONICAL_DOCUMENTATION.md for the inline script
```

If you want containers to start the async gRPC server instead of uvicorn,
set the container env `START_ASYNC_GRPC=1` (entrypoint will launch the async
server on port 50053).
