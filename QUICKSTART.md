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
