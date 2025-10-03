# SomaFractalMemory Kubernetes Playbook

This playbook walks through building a fully functional SomaFractalMemory (SFM) cluster on Kubernetes. It is designed for operators who need a reproducible way to launch the entire enterprise topology (API, consumer, PostgreSQL, Redis, Qdrant, Kafka broker) on a single-machine Kind cluster or a remote Kubernetes environment. (Legacy documents referenced Redpanda; the default local broker has migrated to a Confluent Kafka single-node KRaft image.)

The guide is intentionally detailed, covering host preparation, cluster bootstrap, Helm installation, post-install checks, and common failure recovery. Follow the steps in order for a clean deployment.

---

## 1. Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| macOS or Linux host | 16 GB RAM (8 GB free) | Windows WSL2 works, but commands below assume macOS/Linux shells. |
| Docker Desktop / Engine | 24.x+ | Allocate ≥ 8 GB RAM and ≥ 4 CPU cores to Docker. |
| kubectl | 1.29+ | `brew install kubectl` or vendor CLI. |
| kind | 0.23+ | `brew install kind`. |
| helm | 3.13+ | `brew install helm`. |
| jq | 1.6+ | Used for JSON verification. |

> **Docker resource allocation**: open Docker Desktop → Settings → Resources and ensure at least 8 GB memory and 4 CPUs are available to containers. For lower-spec machines, adjust the values file in step 5 accordingly.

---

## 2. Prepare the repository

```bash
cd somafractalmemory
# Optional: build the image locally if you have pending code changes
docker build -t somafractalmemory:local .
```

If you are using a published image, skip the build and reference the registry tag in step 6.

For a slimmer production-style image (excludes tests, docs, and build toolchain), build the
runtime variant:

```bash
docker build -f Dockerfile.runtime -t somafractalmemory-runtime:local .
```

Then load that tagged runtime image instead of the full dev image in Kind (see step 5).

---

## 3. Create or reset the Kind cluster

1. Delete any existing clusters with conflicting names:

    ```bash
    kind delete cluster --name soma-fractal-memory 2>/dev/null || true
    kind delete cluster --name soma-cluster 2>/dev/null || true
    ```

2. Create the cluster using the repo-provided config:

    ```bash
    kind create cluster --config helm/kind-config.yaml
    ```

   The `helm/kind-config.yaml` file disables aggressive eviction thresholds so the stack can run without premature pod eviction.

3. Set the new context (Kind names the context `kind-soma-fractal-memory`):

    ```bash
    kubectl config use-context kind-soma-fractal-memory
    kubectl cluster-info
    ```

> **Tip**: If you require a multi-node topology, add worker entries to `helm/kind-config.yaml` before creating the cluster.

---

## 4. (Legacy) Increase async I/O capacity for Redpanda

If you are running Redpanda instead of the default Confluent Kafka KRaft broker, it requires a higher `fs.aio-max-nr` value than the Kind default. Apply the tweak to every Kind node:

```bash
for node in $(kind get nodes --name soma-fractal-memory); do
  docker exec "$node" sysctl -w fs.aio-max-nr=524288
  docker exec "$node" sysctl -w vm.max_map_count=262144
done
```

These commands execute inside the Kind node containers and persist for the lifetime of the cluster.

---

## 5. Load or reference the API image

For local iterative work, load the freshly built image into Kind:

```bash
kind load docker-image somafractalmemory-runtime:local --name soma-fractal-memory
```

When using a registry-hosted image, record its coordinates (e.g., `somatechlat/soma-memory-api:v2.1.0`) and configure the Helm chart accordingly in step 6.

---

## 6. Prepare Helm values for Kind

The default `helm/values.yaml` requests production-sized resources (2 Gi per API/consumer). Kind nodes typically cannot schedule those pods. Create a Kind override file with lighter requests (Redpanda resource tuning lines can remain; they are ignored if you swap to Confluent Kafka but the values block name persists for compatibility):

```bash
cat <<'YAML' > helm/values-kind.yaml
resources:
  requests:
    cpu: "300m"
    memory: "768Mi"
  limits:
    cpu: "1200m"
    memory: "1536Mi"

consumer:
  resources:
    requests:
      cpu: "250m"
      memory: "640Mi"
    limits:
      cpu: "1000m"
      memory: "1280Mi"

image:
  repository: somafractalmemory-runtime
  tag: local
  pullPolicy: IfNotPresent

redpanda:
  resources:
    requests:
      cpu: "400m"
      memory: "768Mi"
    limits:
      cpu: "1500m"
      memory: "1536Mi"
  persistence:
    enabled: false

postgres:
  resources:
    requests:
      cpu: "300m"
      memory: "768Mi"
    limits:
      cpu: "600m"
      memory: "1024Mi"
  persistence:
    enabled: false

redis:
  resources:
    requests:
      cpu: "100m"
      memory: "256Mi"
    limits:
      cpu: "400m"
      memory: "512Mi"
  persistence:
    enabled: false

qdrant:
  resources:
    requests:
      cpu: "250m"
      memory: "384Mi"
    limits:
      cpu: "750m"
      memory: "768Mi"
  persistence:
    enabled: false

probe:
  initialDelaySeconds: 25
  timeoutSeconds: 10
YAML
```

Adjust CPU/memory numbers upward if your host can accommodate more headroom. If you are using a registry image, update the `image.repository` and `image.tag` entries instead of the `somafractalmemory:local` defaults above.

---

## 7. Install the Helm chart

1. Ensure the namespace exists:

    ```bash
    kubectl create namespace soma-memory 2>/dev/null || true
    ```

2. Install or upgrade the chart:

    ```bash
    helm upgrade --install soma-memory ./helm \
      --namespace soma-memory \
      --create-namespace \
      --values helm/values.yaml \
      --values helm/values-kind.yaml \
      --wait --timeout=600s
    ```
  ```

3. (Legacy) Reduce Redpanda’s CPU/memory footprint so it stays stable on Kind:

  ```bash
  kubectl patch deployment soma-memory-somafractalmemory-redpanda \
    -n soma-memory --type=json \
    -p='[{"op":"add","path":"/spec/template/spec/containers/0/args","value":["redpanda","start","--smp","1","--overprovisioned","--reserve-memory","0M","--memory","1024M"]}]'
  ```

  Restart the pod to apply the new arguments:

  ```bash
  kubectl rollout restart deployment soma-memory-somafractalmemory-redpanda -n soma-memory
  ```

4. Watch the rollout:
3. Watch the rollout:

    ```bash
    kubectl -n soma-memory get pods -w
    ```
  Continue to the next section once all pods report `Running`.
    Continue to the next section once all pods report `Running`.

---

## 8. Post-install verification

Run the following checks after the chart finishes installing.

1. **Pods and deployments**

    ```bash
    kubectl -n soma-memory get deployments
    kubectl -n soma-memory get pods -o wide
    ```

  Expected deployments: API, (optional consumer if enabled), postgres, redis, qdrant, broker (deployment name may still include `redpanda`).

2. **API health**

    ```bash
    kubectl -n soma-memory port-forward svc/soma-memory-somafractalmemory 9595:9595 >/tmp/sfm-port-forward.log 2>&1 &
    PORT_FWD_PID=$!
    sleep 5
    curl -s http://127.0.0.1:9595/healthz | jq .
    kill $PORT_FWD_PID
    ```

3. **Database check**

    ```bash
    kubectl -n soma-memory exec deploy/soma-memory-somafractalmemory-postgres -- pg_isready -U postgres
    ```

4. **Redis connectivity**

    ```bash
    kubectl -n soma-memory exec deploy/soma-memory-somafractalmemory-redis -- redis-cli ping
    ```

5. **Qdrant status**

    ```bash
    kubectl -n soma-memory exec deploy/soma-memory-somafractalmemory-qdrant -- curl -s localhost:6333/collections | jq .
    ```

6. **Broker liveness (Redpanda legacy)**

    ```bash
    kubectl -n soma-memory exec deploy/soma-memory-somafractalmemory-redpanda -- rpk cluster health
    ```

If any command fails, refer to the troubleshooting section below.

---

## 9. Smoke test the API and eventing

1. Store a single memory (ensure port-forward is active):

    ```bash
    curl -s -X POST http://127.0.0.1:9595/store \
      -H 'Content-Type: application/json' \
      -d '{"coord":"0,0,0","payload":{"text":"hello","run_id":"sanity"},"type":"episodic"}'
    ```

2. Confirm the record exists in PostgreSQL:

    ```bash
    kubectl -n soma-memory exec deploy/soma-memory-somafractalmemory-postgres -- \
      psql -U postgres -d somamemory -t -c "select count(*) from kv_store where value::text like '%sanity%';"
    ```

3. Validate the consumer processed events (look for `Successfully processed event`):

    ```bash
    kubectl -n soma-memory logs deploy/soma-memory-somafractalmemory-consumer | grep -i processed | tail -n 5
    ```

4. Check Qdrant for vectors:

    ```bash
    kubectl -n soma-memory exec deploy/soma-memory-somafractalmemory-qdrant -- \
      curl -s localhost:6333/collections/api_ns/points/count | jq .
    ```

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| API pod `Pending` with `Insufficient memory` | Requests exceed node capacity. | Increase Docker memory or lower `resources.requests` in `values-kind.yaml`. Re-run Helm upgrade. |
| Redpanda `CrashLoopBackOff` with `Could not setup Async I/O` | `fs.aio-max-nr` too low. | Re-run the sysctl loop from step 4 (legacy section) and restart the Redpanda pod. |
| `local-path-provisioner` crash loops | Kind bug after Docker restart. | `kubectl delete pod -n local-path-storage -l app=local-path-provisioner`. |
| Consumer logs show `redis://localhost:6379` | Old deployment revision or missing env override. | Run `helm upgrade` to regenerate the deployment, then delete stale ReplicaSets: `kubectl delete rs -n soma-memory -l app.kubernetes.io/name=somafractalmemory`. |
| API health check fails but pod is running | Evented mode needs backing services | Ensure Redis, Postgres, Qdrant, and broker pods are ready. Examine logs with `kubectl logs`. |

---

## 11. Production adaptations

For real deployments beyond Kind:

- Enable persistence:

  ```bash
  helm upgrade soma-memory ./helm \
    -n soma-memory \
    -f helm/values.yaml \
    -f helm/values-production.yaml \
    --set postgres.persistence.enabled=true \
    --set qdrant.persistence.enabled=true \
    --set redis.persistence.enabled=true \
    --set redpanda.persistence.enabled=true \
    --wait --timeout=600s
  ```

  Provide storage classes or PVC sizes to match your cloud provider.

- Point the chart at registry-hosted images:

  ```bash
  --set image.repository=myregistry.example.com/soma-memory-api \
  --set image.tag=v2.1.0 \
  --set image.pullPolicy=IfNotPresent
  ```

- Secure the API with Ingress + TLS and configure authentication via `SOMA_API_TOKEN` or OIDC proxies.

- Run multiple consumer replicas and consider HorizontalPodAutoscaler resources for API and consumers.

---

## 12. Cleanup

When the experiment is over:

```bash
helm uninstall soma-memory -n soma-memory
kubectl delete namespace soma-memory
kind delete cluster --name soma-fractal-memory
```

Remove the temporary values file if you generated one:

```bash
rm -f helm/values-kind.yaml
```

---

---
### Migration Note: Redpanda → Confluent Kafka
The default development broker has migrated from Redpanda to a single-node Confluent Kafka KRaft image due to intermittent async I/O resource exhaustion on some hosts. Helm values and deployment names may still reference `redpanda`; this is intentional backward compatibility. To continue using Redpanda keep the existing image and follow the legacy tuning steps. To use Confluent Kafka, swap the image and omit Redpanda-only flags—no application code changes are required.

By following this playbook you should consistently achieve a healthy SomaFractalMemory cluster with all supporting pods online. Keep the values file under version control if you customize it further, and revisit this guide whenever the Helm chart gains new components.
