# Secret & Credential Management

This runbook explains how to configure credentials for SomaFractalMemory (SFM) across local Docker Compose, the shared Docker infrastructure, and Kubernetes deployments. It is the authoritative reference for provisioning and rotating the values required by the API, CLI, and background consumers.

---

## 1. Required secrets

| Variable | Purpose | Surfaces | Notes |
|----------|---------|----------|-------|
| `SOMA_API_TOKEN` | Mandatory bearer token enforced by the FastAPI surface (all mutating routes) and CLI. | API, CLI, Consumers | Stored as plain env var for Compose; mounted from Secret in Kubernetes.
| `POSTGRES_URL` | DSN with credentials for the canonical Postgres store. | API, CLI, Consumers | Must set `sslmode=require` (or stronger) in production. |
| `REDIS_URL` | Connection string with optional password for the Redis cache/lock service. | API, Consumers | Optional when Redis disabled; still provision the key for clarity.
| `QDRANT_URL` | HTTPS endpoint (with API key if required) for the vector store. | API, Consumers | If using TLS with self-signed certs, also mount CA bundle.
| `KAFKA_BOOTSTRAP_SERVERS` | SASL- or TLS-enabled broker address used by producer and consumers. | API, Consumers | Additional SASL/TLS env vars (e.g., `KAFKA_SASL_USERNAME`) belong in the same secret. |

Add any deployment-specific secrets (Langfuse keys, OTEL exporters, etc.) to the same secret so they are versioned together.

---

## 2. Local development & shared Docker infra

1. Copy `config.example.yaml` to `config.yaml` (optional) and edit credentials.
2. Export required environment variables in your shell before running `uv run`, `make setup-dev`, or `docker compose`:
   ```bash
   export SOMA_API_TOKEN=dev-token
   export POSTGRES_URL="postgresql://postgres:postgres@localhost:5433/somamemory"
   export REDIS_URL="redis://localhost:6379/0"
   export QDRANT_URL="http://localhost:6333"
   export KAFKA_BOOTSTRAP_SERVERS="localhost:19092"
   ```
3. When reusing the shared Docker infrastructure, override the URLs with the hostnames published by the platform team (see `docs/ops/shared_infra_compose.md`). Keep the token secret outside of the repository (e.g., `.env` ignored by git).

---

## 3. Kubernetes (Helm chart)

### 3.1 Default chart behaviour

- `helm/templates/secret.yaml` renders a Kubernetes Secret when `secret.enabled=true`, no `secret.existingSecret` is provided, and `externalSecret.enabled=false`.
- All keys in `.Values.secret.data` are injected as environment variables for the API and consumer Deployments.
- Setting `secret.existingSecret` allows you to reference a Secret that already exists in the namespace; the chart will not attempt to manage it directly.
- Optional pod annotations can be supplied through `.Values.podAnnotations` or `.Values.secret.rolloutRestart` (see §3.4) to integrate with restart controllers like [Stakater Reloader](https://github.com/stakater/Reloader).

### 3.2 Creating the managed secret

```bash
kubectl create namespace soma-memory
kubectl create secret generic soma-memory-runtime-secrets \
  --namespace soma-memory \
  --from-literal=SOMA_API_TOKEN="replace-me" \
  --from-literal=POSTGRES_URL="postgresql://user:pass@postgres:5432/somamemory?sslmode=require" \
  --from-literal=REDIS_URL="redis://:password@redis:6379/0" \
  --from-literal=QDRANT_URL="https://qdrant.svc.cluster.local:6333" \
  --from-literal=KAFKA_BOOTSTRAP_SERVERS="kafka.svc.cluster.local:9093"
```

Then install/upgrade Helm with:
```bash
helm upgrade --install soma-memory ./helm \
  --namespace soma-memory \
  --set secret.enabled=false \
  --set secret.existingSecret=soma-memory-runtime-secrets \
  --set env.MEMORY_MODE=evented_enterprise \
  --wait --timeout=600s
```

> **Why disable `secret.enabled`?** Setting `.Values.secret.enabled=false` prevents Helm from trying to manage the secret’s lifetime. Rotation then happens entirely through your secret manager (Vault, ExternalSecret, etc.).

### 3.3 Integrating ExternalSecret / Vault

The chart now includes `helm/templates/externalsecret.yaml` so you can declaratively wire External Secrets pointing at Vault, AWS Secrets Manager, or other backends.

The repo ships `helm/values-production.yaml` as a baseline. Customize it or start from the following fragment:

```yaml
secret:
  enabled: false

externalSecret:
  enabled: true
  secretStoreRef:
    name: soma-vault-store
    kind: ClusterSecretStore
  data:
    - secretKey: SOMA_API_TOKEN
      remoteRef:
        key: secret/data/shared-infra/soma-memory/prod
        property: soma_api_token
    - secretKey: POSTGRES_URL
      remoteRef:
        key: secret/data/shared-infra/soma-memory/prod
        property: postgres_dsn
    - secretKey: REDIS_URL
      remoteRef:
        key: secret/data/shared-infra/soma-memory/prod
        property: redis_url
    - secretKey: QDRANT_URL
      remoteRef:
        key: secret/data/shared-infra/soma-memory/prod
        property: qdrant_url
    - secretKey: KAFKA_BOOTSTRAP_SERVERS
      remoteRef:
        key: secret/data/shared-infra/soma-memory/prod
        property: kafka_bootstrap_servers
  target:
    name: soma-memory-runtime-secrets
    template:
      metadata:
        annotations:
          reloader.stakater.com/auto: "true"
```

Key points:

1. Set `secret.enabled=false` so Helm will not render inline secrets.
2. Provide the `secretStoreRef` that matches your External Secret configuration.
3. (Optional but recommended) keep the `reloader.stakater.com/auto` annotation (or add your controller's equivalent) to trigger restarts.
4. If you already have an ExternalSecret managed elsewhere, leave `externalSecret.enabled=false` and simply set `secret.existingSecret` to its target name.

### 3.4 Rotation & rollout restarts

Automation options:

- **With Stakater Reloader (recommended for prod):** set `.Values.secret.rolloutRestart.enabled=true` (already true in `helm/values-production.yaml`). The chart adds `reloader.stakater.com/auto: "true"` to the API and consumer pod templates (or merge any custom annotations from `.Values.secret.rolloutRestart.annotations`). When the backing Secret changes, Reloader triggers a rolling update automatically.
- **Without Reloader:** keep `.Values.secret.rolloutRestart.enabled=false` and run manual restarts after the controller refreshes secrets.

Manual procedure (fallback or verification step):

1. Update the backing secret in your manager (Vault, AWS Secrets Manager, etc.).
2. Wait for the ExternalSecret controller (or manual `kubectl apply`) to update the Kubernetes Secret (`kubectl get secret <name> -o yaml | grep resourceVersion`).
3. Trigger a rolling restart:
  ```bash
  kubectl rollout restart deployment/soma-memory-somafractalmemory -n soma-memory
  kubectl rollout restart deployment/soma-memory-somafractalmemory-consumer -n soma-memory
  ```
4. Monitor `/healthz`, `/readyz`, and consumer logs for successful reconnection.

### 3.5 Install a restart controller

Deploy [Stakater Reloader](https://github.com/stakater/Reloader) (or your platform equivalent) once per cluster so Deployments automatically roll when secrets/configmaps change:

```bash
helm repo add stakater https://stakater.github.io/stakater-charts
helm repo update
helm upgrade --install reloader stakater/reloader --namespace kube-utilities --create-namespace
```

The default `helm/values-production.yaml` already sets `secret.rolloutRestart.enabled=true` and adds the `reloader.stakater.com/auto` annotation so Reloader notices updates.

### 3.6 AWS credentials for backups

`helm/values-production.yaml` enables S3 backups for Postgres and Qdrant. Store AWS access keys (or IRSA token references) in a Kubernetes secret such as `soma-memory-backup-aws`, containing `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION`. Point `.Values.backup.*.awsSecretName` at that secret so the CronJobs can upload dumps. If you rely on IAM roles for service accounts, leave `awsSecretName` empty and set `.Values.backup.serviceAccountName` to the IRSA-enabled account.

---

## 4. TLS certificate distribution

SFM expects TLS everywhere in production. Configure the following alongside secrets:

| Component | Recommended secret keys | Notes |
|-----------|------------------------|-------|
| Postgres | `POSTGRES_SSL_ROOT_CERT`, `POSTGRES_SSL_CERT`, `POSTGRES_SSL_KEY` | Mount as files and reference via env vars in `.Values.env`. |
| Qdrant | `QDRANT_TLS=true`, `QDRANT_TLS_CA_PATH` | Place CA bundle in the same secret; mount via projected volume. |
| Kafka | `KAFKA_SECURITY_PROTOCOL`, `KAFKA_SASL_*`, `KAFKA_SSL_*` | Reuse the runtime secret to keep broker credentials versioned. |

Update `helm/values.yaml` (or an override file) to mount TLS files into the pod and set the matching environment variables. Document the mount paths in `docs/PRODUCTION_READINESS.md` for future operators.

---

## 5. Validation checklist

1. `kubectl get secret soma-memory-runtime-secrets -n soma-memory -o yaml` and confirm expected keys are present (values should show as base64 but not plain text).
2. `kubectl exec deploy/soma-memory-somafractalmemory -n soma-memory -- env | grep SOMA_API_TOKEN` should NOT print anything (token redacted); use `printenv` only for non-sensitive entries.
3. Hit `/healthz` and `/readyz`; confirm logs show `Loaded API token from secret` exactly once on boot.
4. Run `make settings` after deployment to verify Helm NodePort/service addresses if applicable.

For additional operational context, pair this runbook with:
- `docs/PRODUCTION_READINESS.md` (deployment checklist)
- `docs/PORT_FORWARDING_IMPROVEMENTS.md` (incident recovery)
- `docs/CANONICAL_DOCUMENTATION.md#5-configuration-checklist`
