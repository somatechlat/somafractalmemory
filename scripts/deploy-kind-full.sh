#!/usr/bin/env bash
# Create a kind cluster, load local images, and deploy shared infra via Helm.
# Usage: scripts/deploy-kind-full.sh [cluster-name]

set -euo pipefail
CLUSTER_NAME=${1:-soma-kind}
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/scripts"
CHART_DIR="$REPO_ROOT/infra/helm/soma-infra"

if ! command -v kind >/dev/null 2>&1; then
  echo "kind is not installed. Please install kind: https://kind.sigs.k8s.io/" >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is not installed. Please install kubectl." >&2
  exit 1
fi

# Create cluster if not exists
if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
  echo "Creating kind cluster: ${CLUSTER_NAME}"
  kind create cluster --name "${CLUSTER_NAME}"
else
  echo "Kind cluster ${CLUSTER_NAME} already exists"
fi

# Load images (optional) - tries to find images built locally in build/ or load a sample
echo "Loading images into kind (no-op if none found)"
# find images in build/ (if you push tarballs there)
if [[ -d "$REPO_ROOT/build" ]]; then
  for f in "$REPO_ROOT"/build/*.tar; do
    if [[ -f "$f" ]]; then
      echo "Loading image tar $f into kind"
      kind load image-archive "$f" --name "${CLUSTER_NAME}"
    fi
  done
fi

# Deploy shared infra helm chart
if [[ -d "$CHART_DIR" ]]; then
  echo "Deploying Helm chart from $CHART_DIR"
  kubectl create namespace soma-system || true
  helm upgrade --install soma-infra "$CHART_DIR" -n soma-system --wait
else
  echo "Helm chart not found at $CHART_DIR" >&2
  exit 1
fi

echo "Deployment complete. Use 'kubectl -n soma-system get all' to inspect resources."
