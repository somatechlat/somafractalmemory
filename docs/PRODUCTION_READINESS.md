```markdown
# Production Readiness & Deployment Guide

This guide documents how to prepare, deploy and validate a production-capable
Soma Fractal Memory cluster. It combines operational best-practices, the
Helm-based deployment steps used for local Kind clusters and explicit
verification steps for eventing, persistence and vector indexing.

> Note: this guide is intentionally prescriptive so operators can reproduce
> deployments reliably. For development flows (quick iteration) see
> `docs/CANONICAL_DOCUMENTATION.md`.

## 1. Build, tag and push images

Recommended image tags follow semantic versioning plus a short patch label.
Examples below use `2.0-prod` and `2.0-jsonschema-fix` for a local build.

Local build (developer machine):

```bash
# Build a reproducible image locally (adjust tag as needed)
docker build -t somatechlat/somafractalmemory:2.0-jsonschema-fix .

# For local Kubernetes (Kind) load it into the cluster node
kind load docker-image somatechlat/somafractalmemory:2.0-jsonschema-fix --name soma-cluster

# For a remote registry (recommended for production) push the image:
docker tag somatechlat/somafractalmemory:2.0-jsonschema-fix myregistry.example.com/somatechlat/somafractalmemory:2.0-jsonschema-fix
docker push myregistry.example.com/somatechlat/somafractalmemory:2.0-jsonschema-fix
```

Notes:
- Use a private registry or your cloud provider's container registry for
  production, and set imagePullSecrets in Helm if the registry is private.
- Pin base images for reproducible builds (the `Dockerfile` already uses
  `python:3.10-slim` in this repo).

## 2. Helm deployment (Kind or cloud Kubernetes)

Set the namespace and release name. This example uses `soma` namespace and
release `soma-memory`.

```bash
kubectl create namespace soma || true
helm upgrade --install soma-memory ./helm \
  -n soma \
  --values helm/values-production.yaml \
  --set image.tag=2.0-jsonschema-fix \
  --wait

# Check rollout status
kubectl -n soma get pods -l app.kubernetes.io/name=somafractalmemory
kubectl -n soma rollout status deployment/soma-memory-somafractalmemory
kubectl -n soma get pvc
```

If pods don't start, inspect logs:

```bash
kubectl -n soma logs deploy/soma-memory-somafractalmemory --follow
kubectl -n soma describe pod <pod-name>
```

## 3. Key configuration and schema notes

- Ensure `EVENTING_ENABLED=true` in `helm/values.yaml` (or override via `--set`) when using the evented pipeline.
- The event producer validates events against `schemas/memory.event.json`. The project requires `timestamp` as an ISO8601 string (`date-time`). If you extend or change the schema, update both producer and consumers.
- We recommend keeping `additionalProperties: false` in the schema to force strict contract compatibility.

Recent compatibility fix included:

- `eventing/producer.py` now loads `schemas/memory.event.json` and emits UTC ISO8601 timestamps (e.g. `2025-09-27T12:34:56.789+00:00`).
- `workers/kv_writer.py` accepts numeric epoch or ISO timestamp strings and normalizes to epoch seconds before DB insertion. This keeps backward compatibility.

## 4. Expose API for developers (local dev only)

- Use `kubectl port-forward` for a single machine: `kubectl -n soma port-forward svc/soma-memory-somafractalmemory 9595:9595`.
- Prefer the idempotent helper `./scripts/port_forward_api.sh start`; it wraps
  the port-forward in `nohup`, records the PID in `/tmp/port-forward-*.pid`, and
  frees the terminal while continuing to stream logs to `/tmp/port-forward-*.log`.

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
items = [{"id": str(uuid.uuid4()), "text": f"item {i}", "run_id": run_id} for i in range(50)]
resp = requests.post('http://localhost:9595/store_bulk', json={"items": items})
print(resp.status_code, resp.text)
PY
```

3. Verify Postgres persistence (from the Postgres pod to avoid networking differences):

```bash
kubectl exec -n soma deploy/soma-memory-somafractalmemory-postgres -- \
  -- psql -U postgres -d somamemory -t -c "select count(*) from public.kv_store where value::text like '%<RUN_ID>%';"
```

4. Verify Qdrant indexing:

```bash
curl -s http://$(kubectl -n soma get svc soma-memory-somafractalmemory-qdrant -o jsonpath='{.spec.clusterIP}'):6333/collections/api_ns | jq .
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
- Missing vectors in Qdrant: check consumer logs (`kubectl -n soma logs deploy/soma-memory-somafractalmemory-consumer`) and verify `workers/vector_indexer.py` is running without exceptions.

## 9. Production recommendations

- Use managed Postgres and Qdrant where possible to get durable persistence and backups.
- Use a managed Kafka (or a hardened Redpanda cluster) with appropriate retention and replication settings.
- Deploy with resource requests/limits and HorizontalPodAutoscalers for the API and consumers.
- Secure the cluster: use network policies, TLS for Kafka if available, and protect the API with authentication (SOMA_API_TOKEN) and an ingress controller with TLS.

## 10. Rollback procedure

```bash
# Roll back to previous chart revision
helm rollback soma-memory 1 -n soma
kubectl -n soma rollout status deployment/soma-memory-somafractalmemory
```

---

Keep this guide up to date as the project evolves. If you change the schema or event contract, update `schemas/memory.event.json` as the canonical source of truth and increment the library version.

```
