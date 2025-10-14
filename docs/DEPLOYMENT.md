# Deployment reference (Compose, Kind + Helm)

This file is a short, canonical summary that points you to the detailed
deployment instructions in the repository.

1) Local development (Docker Compose)

- Canonical entrypoint: `docker-compose.yml` (root of repo). Use Compose
  profiles to select services. The Memory API is fixed to host port `9595`.

  - Start the full local stack (auto-assign infra ports):
    ```bash
    make setup-dev
    # OR
    ./scripts/assign_ports_and_start.sh
    ```

  - Start only shared infra (Kafka/Postgres/Redis/Qdrant):
    ```bash
    docker compose --profile shared up -d
    ```

  - Start consumer only:
    ```bash
    docker compose --profile consumer up -d somafractalmemory_kube
    ```

2) Local Kubernetes dev slice (Kind + Helm)

- Use Kind + Helm when you need cluster parity or to test Helm charts.

  - Create Kind cluster and install dev chart (exposes NodePort 30797 by default):
    ```bash
    make setup-dev-k8s
    make helm-dev-health
    ```

3) Production (Helm)

- Use `helm/values-production.yaml` and override storage classes and image coordinates.

  ```bash
  helm upgrade --install soma-memory ./helm -n soma-memory --values helm/values-production.yaml --wait
  ```

4) Troubleshooting & diagnostics

- See `docs/CANONICAL_DOCUMENTATION.md::Troubleshooting` and `docs/ARCHITECTURE.md` for troubleshooting steps, consumer restart instructions, and the automatic port assignment behavior.

This file is intentionally concise; for detailed step-by-step workflows see:
- `docs/CANONICAL_DOCUMENTATION.md` (operational source of truth)
- `docs/ARCHITECTURE.md` (architecture and Docker modes)
- `docs/DEVELOPER_ENVIRONMENT.md` (environment setup, uv, and more)
