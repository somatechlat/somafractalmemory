#!/usr/bin/env bash
# Deploy the Soma shared infrastructure chart into the Kind cluster.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHART_DIR="${REPO_ROOT}/infra/helm/soma-infra"
MODE="${MODE:-${1:-dev}}"
NAMESPACE="${NAMESPACE:-soma-infra}"
TIMEOUT="${TIMEOUT:-300s}"

BASE_VALUES="${CHART_DIR}/values.yaml"
MODE_VALUES="${CHART_DIR}/values-${MODE}.yaml"

require_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required tool: $1" >&2
    exit 1
  fi
}

main() {
  require_tool helm
  require_tool kubectl

  if [[ ! -d "$CHART_DIR" ]]; then
    echo "Shared infra chart directory not found at $CHART_DIR" >&2
    exit 1
  fi

  if [[ ! -f "$BASE_VALUES" ]]; then
    echo "Base values file missing at $BASE_VALUES" >&2
    exit 1
  fi

  if [[ ! -f "$MODE_VALUES" ]]; then
    echo "Mode-specific values file missing at $MODE_VALUES" >&2
    exit 1
  fi

  echo "Updating Helm dependencies..."
  helm dependency update "$CHART_DIR"

  echo "Ensuring namespace ${NAMESPACE}"
  kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

  echo "Deploying shared infrastructure (mode=${MODE})"
  helm upgrade --install sharedinfra "$CHART_DIR" \
    -n "${NAMESPACE}" \
    -f "$BASE_VALUES" \
    -f "$MODE_VALUES" \
    --wait --timeout "${TIMEOUT}"

  echo "Waiting for pods to become ready..."
  kubectl wait --for=condition=Ready pod --all -n "${NAMESPACE}" --timeout "${TIMEOUT}"

  echo "Deployment complete. Current pod status:"
  kubectl get pods -n "${NAMESPACE}"
}

main "$@"
