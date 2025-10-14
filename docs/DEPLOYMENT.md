# Deployment reference (Compose, Kind + Helm)

This file is a short, canonical summary that points you to the detailed
deployment instructions in the repository.

## 1. Local development (Docker Compose)

The recommended way to start the complete stack is to use the automatic port assignment script. This will prevent conflicts with any other services running on your machine.

### One-Command Zero-Conflict Deployment
```bash
# Automatic port assignment with conflict resolution
./scripts/assign_ports_and_start.sh

# OR use make target
make setup-dev
```

**Features:**
- ✅ **Automatic port conflict detection and resolution**
- ✅ **Complete evented enterprise stack** (API + Consumer + All Infrastructure)
- ✅ **Persistent volumes** for data retention across restarts
- ✅ **Zero-configuration deployment** with real services (no mocks)
- ✅ **Memory API fixed on port 9595** (never conflicts)
- ✅ **All infrastructure ports auto-assigned** (PostgreSQL, Redis, Qdrant, Kafka)

**Access Points:**
- Memory API: http://localhost:9595 (fixed)
- Infrastructure: Auto-assigned ports (displayed at startup)
- Port assignments saved to: `.env`

## 2. Local Kubernetes dev slice (Kind + Helm)

- Use Kind + Helm when you need cluster parity or to test Helm charts.

  - Create Kind cluster and install dev chart (exposes NodePort 30797 by default):
    ```bash
    make setup-dev-k8s
    make helm-dev-health
    ```

## 3. Production (Helm)

- Use `helm/values-production.yaml` and override storage classes and image coordinates.

  ```bash
  helm upgrade --install soma-memory ./helm -n soma-memory --values helm/values-production.yaml --wait
  ```

## 4. Troubleshooting & diagnostics

- See `docs/CANONICAL_DOCUMENTATION.md::Troubleshooting` and `docs/ARCHITECTURE.md` for troubleshooting steps, consumer restart instructions, and the automatic port assignment behavior.

This file is intentionally concise; for detailed step-by-step workflows see:
- `docs/CANONICAL_DOCUMENTATION.md` (operational source of truth)
- `docs/ARCHITECTURE.md` (architecture and Docker modes)
- `docs/DEVELOPER_ENVIRONMENT.md` (environment setup, uv, and more)
