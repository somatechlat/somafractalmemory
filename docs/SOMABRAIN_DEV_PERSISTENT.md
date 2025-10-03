# Somabrain Dev Persistent Environment

This guide provisions a **developer-oriented yet production-shaped** cluster deployment of Soma Fractal Memory with:

- All real backing services: Postgres, Redis (AOF), Qdrant, Redpanda (Kafka API)
- Evented enterprise wiring (publish + consume memory.events)
- Persistence enabled for every datastore and broker
- Dedicated namespace + consumer group (`somabrain_ns`, `somabrain-consumer-group`)
- Stable API port override (9696) to avoid local 9595 conflicts

## Values File
Use `helm/values-dev-full-persistent.yaml` (created for this purpose).

## Deploy
```bash
# (Optional) load local runtime image into Kind
docker build -f Dockerfile.runtime -t somafractalmemory-runtime:dev .
kind load docker-image somafractalmemory-runtime:dev --name somabrain-cluster || true

helm upgrade --install somabrain ./helm \
  -n somabrain --create-namespace \
  -f helm/values.yaml \
  -f helm/values-dev-full-persistent.yaml \
  --set image.tag=dev \
  --wait --timeout=600s
```

Port-forward:
```bash
kubectl -n somabrain port-forward svc/somabrain-somafractalmemory 9696:9696 &
sleep 3
curl -sf http://localhost:9696/healthz
```

## Smoke Insert & Recall
```bash
curl -X POST http://localhost:9696/store \
  -H 'Content-Type: application/json' \
  -d '{"coord":"11,22,33","payload":{"task":"persist-check","importance":4},"type":"episodic"}'

curl -X POST http://localhost:9696/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"persist-check"}' | jq '.matches[0]'
```

## Persistence Verification Workflow
1. Insert a marker memory (as above) and note coordinate.
2. Retrieve stats:
   ```bash
   curl -s http://localhost:9696/stats | jq
   ```
3. Delete API pod:
   ```bash
   kubectl -n somabrain delete pod -l app.kubernetes.io/name=somafractalmemory,app.kubernetes.io/component=api
   kubectl -n somabrain wait --for=condition=ready pod -l app.kubernetes.io/component=api --timeout=120s
   ```
4. Re-query stats and recall; marker should still be present.
5. Delete Postgres pod only:
   ```bash
   kubectl -n somabrain delete pod -l app.kubernetes.io/name=somafractalmemory,app.kubernetes.io/component=postgres
   kubectl -n somabrain wait --for=condition=ready pod -l app.kubernetes.io/component=postgres --timeout=180s
   ```
6. Re-check recall again (durable row still present).
7. (Optional) Delete Qdrant pod and validate recall for semantic vectors still works—embedding may repopulate if async indexing occurs.
8. Produce memory events and tail consumer:
   ```bash
   kubectl -n somabrain logs -l app.kubernetes.io/component=consumer -f --tail=50
   ```

## Event Bus Quick Check
List topics (exec ephemeral pod):
```bash
kubectl -n somabrain run rpk --image=docker.redpanda.com/redpandadata/redpanda:v23.1.13 -it --rm --command -- \
  rpk cluster info --brokers somabrain-somafractalmemory-redpanda:9092
kubectl -n somabrain run rpk2 --image=docker.redpanda.com/redpandadata/redpanda:v23.1.13 -it --rm --command -- \
  rpk topic list --brokers somabrain-somafractalmemory-redpanda:9092
```

## Tear Down (Keep Volumes)
```bash
helm uninstall somabrain -n somabrain
# PVCs remain (reuse state).
```

## Full Reset (Remove Data)
```bash
helm uninstall somabrain -n somabrain || true
kubectl delete namespace somabrain --wait=false
# If cluster supports, ensure PVC deletion finalizers cleared automatically.
```

## Recommended Next Hardening
- Add Ingress with TLS termination (nginx/traefik + cert-manager)
- Resource tuning via metrics baselines
- Backup strategy (Postgres logical dumps, Qdrant snapshot, Redpanda tiered storage)
- PodDisruptionBudgets for API + Postgres + Redpanda
- Horizontal Pod Autoscaler for API once metrics exported into custom metrics pipeline

---
**Status**: Developer persistent profile ready for use.
