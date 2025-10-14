# Deployment Guide

This document provides a high-level summary of the deployment options for Soma Fractal Memory. For a more detailed explanation, including step-by-step instructions and diagrams, please see the **[Developer User Manual](DEVELOPER_MANUAL.md)**.

## Unified Deployment Workflow

This project uses a `Makefile` as a single entry point for managing all deployments, whether you are running the application locally with Docker Compose or deploying it to a Kubernetes cluster with Helm.

---

## Docker Compose for Local Development

For local development, the project uses Docker Compose to spin up the entire application stack. The configuration is managed in the `docker-compose.yml` file, which uses profiles to separate services.

### Key Commands
- **Start the full stack**: `make compose-up`
- **Stop the stack**: `make compose-down`
- **Build images**: `make compose-build`
- **View logs**: `make compose-logs`

For more details on the Docker Compose setup, see the **[Developer Guide](DEVELOPER_GUIDE.md)**.

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

## 4. Kubernetes Deployment (Helm)

For deploying to Kubernetes, this project includes a Helm chart located in the `helm/` directory. The chart is designed to be flexible and supports two main deployment profiles:

- **LOCAL DEV PROD**: A lightweight configuration for local Kubernetes clusters (e.g., Minikube, Docker Desktop).
- **PROD (HA)**: A high-availability configuration for production environments.

### Deploying for Local Development
To deploy the application to a local Kubernetes cluster, run:
```bash
make helm-install-local-dev
```
This command will create a new namespace, `somafractalmemory-local-dev`, and deploy the application with a single replica for each service and with persistence disabled.

To uninstall the local development deployment:
```bash
make helm-uninstall-local-dev
```

### Deploying for Production (HA)
To deploy the application to a production Kubernetes cluster, run:
```bash
make helm-install-prod-ha
```
This command will create a new namespace, `somafractalmemory-prod-ha`, and deploy the application with multiple replicas and persistent storage.

**Note**: Before deploying to production, you should review and customize the `helm/values-prod-ha.yaml` file to match your cloud provider's storage class and other specific configuration needs.

To uninstall the production deployment:
```bash
make helm-uninstall-prod-ha
```

For more details on configuring the Helm chart, see the `helm/values.yaml` file.

## 5. Troubleshooting & diagnostics

- See `docs/CANONICAL_DOCUMENTATION.md::Troubleshooting` and `docs/ARCHITECTURE.md` for troubleshooting steps, consumer restart instructions, and the automatic port assignment behavior.

This file is intentionally concise; for detailed step-by-step workflows see:
- `docs/CANONICAL_DOCUMENTATION.md` (operational source of truth)
- `docs/ARCHITECTURE.md` (architecture and Docker modes)
- `docs/DEVELOPER_ENVIRONMENT.md` (environment setup, uv, and more)
