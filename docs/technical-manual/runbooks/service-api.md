---
title: "Runbook: API Server"
purpose: "To provide operational procedures for managing the SomaFractalMemory API server."
audience: ["SREs", "DevOps"]
version: "1.0.0"
last_updated: "2025-10-16"
---

# Runbook: API Server

### How to Check Service Status
```bash
# For Docker Compose
docker compose ps api

# For Kubernetes
kubectl get pods -l app=somafractalmemory
```

### How to View Logs
```bash
# For Docker Compose
docker compose logs -f api

# For Kubernetes
kubectl logs -f -l app=somafractalmemory
```

### How to Restart the Service
```bash
# For Docker Compose
docker compose restart api

# For Kubernetes
kubectl rollout restart deployment somafractalmemory-somafractalmemory
```
