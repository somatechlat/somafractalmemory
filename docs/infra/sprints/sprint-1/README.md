# Sprint 1 — Kubernetes Baseline

Collect logs and validation evidence for Sprint 1 acceptance criteria:

1. `infra/kind/soma-kind.yaml` present and used.
2. `scripts/create-kind-soma.sh`, `scripts/preload-sharedinfra-images.sh`, `scripts/deploy-kind-sharedinfra.sh` executed successfully.
3. `make sharedinfra-kind MODE=<mode>` end-to-end run completes with Helm wait gates and Kubernetes pods ready.

## Suggested Artefacts
- `create-kind-soma.log`: output from provisioning the Kind cluster.
- `preload-images.log`: excerpt showing images pulled and loaded.
- `deploy-sharedinfra.log`: Helm upgrade output + `kubectl wait` success.
- `kubectl-get-pods.txt`: namespace listing post-deploy (`kubectl get pods -n soma-infra`).
- `helm-status.txt`: `helm status sharedinfra -n soma-infra`.

Document any deviations or follow-up actions needed before promoting to Sprint 2.
