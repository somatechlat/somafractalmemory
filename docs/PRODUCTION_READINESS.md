# Production Readiness & Deployment Guide

- Local Docker Compose: persistent volumes enabled for Postgres, Redis (AOF), Qdrant, and Kafka. Verified persistence by inserting a record, restarting services, and confirming presence in Postgres (`kv_store`) afterward. API recall requires the background consumer when running in `EVENTED_ENTERPRISE` mode.
- Kubernetes via Helm (dev release on port 9797): API exposed through NodePort 30797 on localhost when using `helm/values-dev-port9797.yaml`. By default, persistence is disabled for convenience; enable per-service `persistence.enabled: true` (or apply `k8s/pvcs.yaml` for Kind) to make data durable.

Gap analysis for production hardening (local limitations noted):
- Authentication and authorization
  - API now enforces `SOMA_API_TOKEN` by default. Next actions: manage secrets centrally, rotate credentials, and front the service with an ingress providing TLS and additional authZ (e.g., OIDC). See `docs/ops/SECRET_MANAGEMENT.md`.
- TLS everywhere
  - Ingress defaults to TLS and Helm DSNs append `sslmode=require`; NEEDS_ACTION: provision certificates/CA bundles, mount them via the runtime secret, and enable upstream TLS where available.
- Secrets management
  - Helm supports inline secrets for dev and an ExternalSecret for production deployments. NEEDS_ACTION: supply `helm/values-production.yaml`, point `externalSecret.secretStoreRef` at Vault (`secret/data/shared-infra/soma-memory/<env>`), install a restart controller (e.g., Stakater Reloader), provision the S3 credentials secret (`soma-memory-backup-aws`), and record rotation evidence.
- Persistence and backups
  - DEV chart disables PVCs. NEEDS_ACTION: enable PVCs with a production StorageClass; configure the provided S3 backup CronJobs (Postgres + Qdrant) and complete a tested restore runbook.
- Database migrations
  - Alembic baseline now tracks `kv_store` and `memory_events`. TODO: wire `make db-upgrade` (i.e. `alembic upgrade head`) into deploy pipelines and add a CI check that `alembic current` matches `head`. See `docs/ops/MIGRATIONS.md` for the runbook.
- High availability and auto-scaling
  - HorizontalPodAutoscalers are available for the API and consumer deployments via `hpa.*` values (production defaults enable them). TODO: consider managed multi-AZ Postgres/Qdrant/Kafka.
- Network policies and RBAC
  - Chart now ships with an optional deny-by-default `NetworkPolicy`; enable it via `networkPolicy.enabled` and tailor ingress/egress selectors for your cluster. TODO: audit RBAC bindings for least privilege.
- Security context & image hardening
  - Deployments now default to non-root pods with RuntimeDefault seccomp, read-only root filesystems, and dropped Linux capabilities. TODO: pin image digests and integrate supply-chain scanning.
- Observability
  - Helm now exposes Prometheus scraping via ServiceMonitor (API + consumer) and optional scrape annotations (see `docs/ops/OBSERVABILITY.md`). TODO: layer Grafana dashboards, alert rules, and OTEL/exporter wiring.
- Resilience to backend restarts
  - Observed a transient `psycopg2.InterfaceError: connection already closed` in `/stats` after Postgres restart. NEEDS_ACTION: add reconnect-on-failure logic in `PostgresKeyValueStore` and make stats robust to backend churn.
---

## Production preflight checklist

1. **Secrets present** – Apply `helm/values-production.yaml` (or equivalent) so secrets flow from Vault via ExternalSecret. Confirm `SOMA_API_TOKEN`, database, Redis, Qdrant, and Kafka credentials are populated in `soma-memory-runtime-secrets`.
2. **TLS assets mounted** – Provide CA bundles/client certs for Postgres, Qdrant, and Kafka as needed. Set `POSTGRES_SSL_*`, `QDRANT_TLS`, and `KAFKA_SECURITY_PROTOCOL` env vars accordingly.
3. **Persistence enabled** – Review `helm/values-production.yaml`; ensure PVC sizes and storageClasses match the target environment. Verify S3 buckets and retention for both Postgres and Qdrant backups.
4. **Migrations** – Run `make db-upgrade` (or `uv run alembic upgrade head`) against Postgres before traffic. Capture revision output in the change log and ensure a rollback plan exists.
5. **Kafka readiness** – Create topics with required replication, enable idempotent producers, and configure DLQs. Update `workers/vector_indexer.py` settings via Helm values.
6. **Observability** – Enable ServiceMonitor (or scrape annotations) for API and consumer, configure OTEL exporters and structured logging sinks, and validate dashboards + alert thresholds.
7. **Access controls** – Lock down ingress with OIDC (or managed auth), define NetworkPolicies, and audit RBAC bindings.
8. **Backup CronJobs running** – Confirm `CronJob/soma-memory-somafractalmemory-postgres-backup` and `CronJob/soma-memory-somafractalmemory-qdrant-backup` complete successfully and publish to the expected S3 prefixes.
9. **Restart controller installed** – Deploy Stakater Reloader (or equivalent) in the cluster so pods roll on secret rotation.
10. **Disaster recovery drill** – Execute the reset + restore workflow end-to-end (database restore, WAL replay, vector rebuild) before go-live.

Document completion evidence for each step in `docs/PRODUCTION_READY_GAP.md`.
This guide documents how to prepare, deploy and validate a production-capable
Soma Fractal Memory cluster. It combines operational best-practices, the
Helm-based deployment steps used for local Kind clusters and explicit
verification steps for eventing, persistence and vector indexing. Refer to
[§ 9 Storage & Persistence Reference](CANONICAL_DOCUMENTATION.md#9-storage--persistence-reference)
for a component-by-component map of where data lives across Docker, Helm, and raw Kubernetes manifests.

> Note: this guide is intentionally prescriptive so operators can reproduce
> deployments reliably. For development flows (quick iteration) see
> `docs/CANONICAL_DOCUMENTATION.md`.

## 1. Build, tag and push images

Recommended image tags follow semantic versioning plus a short patch label.
Examples below use `v2.1.0` and `v2.1.0-rc1` for a local build.

Local build (developer machine):

```bash
# Build a reproducible image locally (adjust tag as needed)
docker build -t somatechlat/soma-memory-api:v2.1.0 .

# For local Kubernetes (Kind) load it into the cluster node
kind load docker-image somatechlat/soma-memory-api:v2.1.0 --name soma-cluster

# For a remote registry (recommended for production) push the image:
docker tag somatechlat/soma-memory-api:v2.1.0 myregistry.example.com/somatechlat/soma-memory-api:v2.1.0
docker push myregistry.example.com/somatechlat/soma-memory-api:v2.1.0
```

Notes:
- Use a private registry or your cloud provider's container registry for
  production, and set imagePullSecrets in Helm if the registry is private.
- Pin base images for reproducible builds (the Dockerfiles in this repo
  use pinned Python slim images; verify they match your runtime policy).

## 2. Helm deployment (Kind or cloud Kubernetes)

Set the namespace and release name. This example uses the `soma-memory`
namespace and release `soma-memory`.

```bash
kubectl create namespace soma-memory || true
helm upgrade --install soma-memory ./helm \
  -n soma-memory \
  --values helm/values-production.yaml \
  --set image.tag=v2.1.0 \
  --wait

# Check rollout status
kubectl -n soma-memory get pods -l app.kubernetes.io/name=somafractalmemory
kubectl -n soma-memory rollout status deployment/soma-memory-somafractalmemory
kubectl -n soma-memory get pvc
```

If pods don't start, inspect logs:

```bash
kubectl -n soma-memory logs deploy/soma-memory-somafractalmemory --follow
kubectl -n soma-memory describe pod <pod-name>
```

## 3. Key configuration and schema notes

- Ensure `EVENTING_ENABLED=true` in `helm/values.yaml` (or override via `--set`) when using the evented pipeline.
- The event producer validates events against `schemas/memory.event.json`. The current implementation emits a numeric epoch timestamp via `time.time()`; consumers accept both epoch numbers and ISO8601 strings and normalise to epoch seconds. If you extend or change the schema, update both producer and consumers.
- We recommend keeping `additionalProperties: false` in the schema to force strict contract compatibility.

## 4. Expose API for developers (local dev only)

- Use `kubectl port-forward` for a single machine: `kubectl -n soma-memory port-forward svc/soma-memory-somafractalmemory 9595:9595`.
- Prefer the idempotent helper `./scripts/port_forward_api.sh start`; it wraps
  the port-forward in `nohup`, records the PID in `/tmp/port-forward-*.pid`, and
  frees the terminal while continuing to stream logs to `/tmp/port-forward-*.log`.
 - When using the provided dev values (`helm/values-dev-port9797.yaml`) the API is exposed via NodePort on your host at `http://127.0.0.1:30797` (service port 9797 inside the cluster).

## 5. Testing & verification (end-to-end)

1. Basic health:

```bash
curl -s http://localhost:9595/healthz | jq .
```

2. Single / small batch store (recommended before full load):

```bash
# Using a short Python script to POST N small items in a loop (chunk size 50)
python - <<'PY'
import requests, uuid, json
run_id = uuid.uuid4().hex
items = [{"coord":"0,0,0","payload":{"text": f"item {i}", "run_id": run_id}, "type":"episodic"} for i in range(50)]
resp = requests.post('http://localhost:9595/store_bulk', json={"items": items})
print(resp.status_code, resp.text)
PY
```

3. Verify Postgres persistence (from the Postgres pod to avoid networking differences):

```bash
kubectl exec -n soma-memory deploy/soma-memory-somafractalmemory-postgres -- \
  -- psql -U postgres -d somamemory -t -c "select count(*) from public.memory_events where payload::text like '%<RUN_ID>%';"
```

4. Verify Qdrant indexing:

```bash
curl -s http://$(kubectl -n soma-memory get svc soma-memory-somafractalmemory-qdrant -o jsonpath='{.spec.clusterIP}'):6333/collections/api_ns | jq .
```

5. If you need to run a large bulk test (1000 items) prefer chunking:

```bash
# Example: 1000 items split into 10 chunks of 100
for i in {1..10}; do
  python post_chunk.py --size 100 --endpoint http://localhost:9595/store_bulk
done
```

Avoid single huge HTTP requests — port-forward and reverse-proxy timeouts make large single requests brittle.

## 6. Consumer scaling and performance

- The `consumer` deployment reads `KAFKA_BOOTSTRAP_SERVERS` and can be scaled independently. If ingest latency is high, increase consumer replicas to reduce backlog.
- For the API ingest path, tune `UVICORN_WORKERS` and allocate CPU for the API pod to accept concurrent uploads.

## 7. Monitoring & alerts

- Export Prometheus metrics (the API and the consumer already expose metrics). Scrape with your Prometheus job and set alerts for:
  - consumer lag (Kafka offsets behind high watermark)
  - qdrant put failures
  - high DB write latency
- Add log collection (Fluentd/Vector/ELK) to capture `Failed to publish memory event` or validation errors.

## 8. Troubleshooting checklist

- Validation errors: check `api` logs for schema validation failures and ensure producer & schema are in sync.
- Timeouts: increase poster HTTP timeouts or use chunked uploads; consider increasing `UVICORN_WORKERS`.
- Missing vectors in Qdrant: check consumer logs (`kubectl -n soma-memory logs deploy/soma-memory-somafractalmemory-consumer`) and verify `workers/vector_indexer.py` is running without exceptions.

## 9. Production recommendations

- Use managed Postgres and Qdrant where possible to get durable persistence and backups.
- Use a managed Kafka (or a hardened Redpanda cluster) with appropriate retention and replication settings.
- Deploy with resource requests/limits and HorizontalPodAutoscalers for the API and consumers.
- Secure the cluster: use network policies, TLS for Kafka if available, and protect the API with authentication (SOMA_API_TOKEN) and an ingress controller with TLS.
 - Enable persistence in Helm values (PVCs) and configure scheduled backups; verify restore.
 - Add PodDisruptionBudgets and health-probe tuning to avoid false positives during rollouts.

## 10. Rollback procedure

```bash
# Roll back to previous chart revision
helm rollback soma-memory 1 -n soma-memory
kubectl -n soma-memory rollout status deployment/soma-memory-somafractalmemory
```

---

Keep this guide up to date as the project evolves. If you change the schema or event contract, update `schemas/memory.event.json` as the canonical source of truth and increment the library version.

```
