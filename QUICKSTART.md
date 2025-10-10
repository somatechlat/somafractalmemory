# SomaFractalMemory - Quick Start

## 🚀 Automatic Server Startup

### One-Command Auto Start:
```bash
./scripts/auto-server.sh
```

This script will:
- ✅ Wait for all Kubernetes pods to be ready
- ✅ Automatically detect the API pod
- ✅ Set up port forwarding on port 9595
- ✅ Test server connectivity
- ✅ Show you all available endpoints
- ✅ Keep running automatically until you stop it

### Server Access:
- **URL**: http://localhost:9595
- **Health**: http://localhost:9595/healthz
- **Stats**: http://localhost:9595/stats
- **API Docs**: http://localhost:9595/docs

### Manual Commands (if needed):
```bash
# Check pods
kubectl get pods -l app.kubernetes.io/instance=soma-memory

# Manual port forward
kubectl port-forward <pod-name> 9595:9595

# Quick test
curl http://localhost:9595/healthz
```

## ⚡ **Just run `./scripts/auto-server.sh` and everything works automatically!**

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
