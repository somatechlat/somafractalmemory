# Lens Integration Guide

This runbook shows operators how to inspect and manage Soma Fractal Memory (SFM) clusters using [Lens](https://k8slens.dev), the Kubernetes IDE. Lens works on top of kubeconfig contexts, so the chart needs to expose standard Kubernetes metadata and developers need a reliable way to point Lens at the active cluster.

## 1. Prerequisites

- Lens Desktop v2024.11 or newer (macOS, Windows, or Linux).
- A running Kubernetes cluster that already hosts the SFM Helm release (kind, shared infra, or cloud).
- Access to the kubeconfig context for that cluster.
- Optional: metrics source (Kubernetes metrics-server or Prometheus Adapter) to power Lens resource graphs.

## 2. Export the kubeconfig for Lens

### 2.1 Kind (local)
```bash
# Replace sfm with your kind cluster name
kind get kubeconfig --name sfm > ~/.kube/config-kind-sfm
```
Then import the file in Lens (`File → Add Cluster… → Browse kubeconfig`).

### 2.2 Shared infra / remote cluster
1. Authenticate with the cluster (for example via `aws eks update-kubeconfig`, `gcloud container clusters get-credentials`, or your SSO wrapper).
2. Export just the required context:
   ```bash
   kubectl config view --minify --flatten > ~/.kube/config-soma-prod
   ```
3. In Lens, click **Add Cluster**, select the exported kubeconfig, and pick the `soma-memory` namespace as a workspace default.

> Tip: keep kubeconfig files in `~/.kube/` and use Lens workspace folders to separate environments (dev / staging / prod).

## 3. Helm release visibility

The Helm chart now emits the standard `app.kubernetes.io/*` label set (name, instance, part-of, version, managed-by). Lens groups workloads by those keys, so Deployments, Services, StatefulSets, and Secrets show up under the same Helm release. If resources appear under "Orphaned" in Lens, run:
```bash
kubectl -n soma-memory label deploy <name> app.kubernetes.io/part-of=somafractalmemory --overwrite
```
and check your Helm overrides for custom selectors.

## 4. Observability inside Lens

- **Metrics**: Install `metrics-server` on dev clusters or configure the Prometheus Adapter (shared infra already includes Prometheus). Without it, Lens graphs display "No metrics".
- **Logs**: Use the Log tab on each Pod; Lens tails all containers and supports filtering by container name (e.g., `somafractalmemory`, `consumer`).
- **Events**: Lens shows Kubernetes events per namespace. Target `soma-memory` and sort by timestamp to catch rollout errors quickly.

## 5. Port-forwarding and terminal access

Lens can port-forward the API and consumer pods for quick testing:
1. Right-click the `somafractalmemory` Service → **Port Forward…** → map `9595` to localhost.
2. Access the API at `http://127.0.0.1:9595/healthz`.
3. Use the built-in Terminal to run `kubectl` commands with the selected context; environment variables inherit from Lens.

## 6. RBAC and security considerations

- Grant operators the `view` ClusterRole (at minimum) so Lens can list and watch workloads. For debugging with logs and exec, use `edit` or a custom role that includes `pods/log` and `pods/exec` verbs.
- Never store production kubeconfigs in Git or shared drives. Use an OS keychain or Lens' encrypted store.
- Disable `secret.enabled` in the Helm values if you rely on ExternalSecret/Vault; Lens will still display metadata while keeping sensitive values out of manifests.

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Helm release does not appear under **Helm Releases** | Ensure the release was installed with Helm ≥3. Lens reads from `helm list`. Run `helm list -n soma-memory` to confirm the release exists. |
| Workloads grouped as `unknown` | Confirm `app.kubernetes.io/part-of` and `app.kubernetes.io/version` labels exist. The chart now sets them, but custom manifests must do the same. |
| "No metrics" everywhere | Deploy `metrics-server` (`kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`) or configure `helm/values-observability.yaml` once available. |
| Lens cannot connect after importing kubeconfig | Check that your auth plugin (OIDC, exec) is installed locally. Run `kubectl get nodes` with the same kubeconfig to verify before retrying in Lens. |

## 8. Next steps

- Automate kubeconfig distribution for shared infra (e.g., via SSO portal download).
- Document Lens workspace conventions in `docs/ops/ONCALL_RUNBOOK.md` during the oncall readiness sprint.
- Add a Prometheus Adapter overlay so Lens can show CPU/Memory graphs without extra steps.
