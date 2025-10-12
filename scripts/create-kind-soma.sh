#!/usr/bin/env bash
# Provision a Kind cluster that matches the SomaStack shared infra baseline.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KIND_CONFIG="${REPO_ROOT}/infra/kind/soma-kind.yaml"
CLUSTER_NAME="${KIND_CLUSTER_NAME:-soma}"

declare -A REQUIRED_VERSIONS=(
  [kubectl]="1.28.0"
  [helm]="3.13.0"
  [kind]="0.22.0"
  [docker]="24.0.0"
  [jq]="1.6"
)

require_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required tool: $1" >&2
    exit 1
  fi
}

normalize_version() {
  local version="${1#v}"
  version="${version%%+*}"
  echo "${version}"
}

ensure_minimum_version() {
  local tool="$1"
  local required="${REQUIRED_VERSIONS[$tool]}"
  local current

  case "$tool" in
    kubectl)
      current="$(kubectl version --client --short | awk '{print $3}')"
      ;;
    helm)
      current="$(helm version --short | awk '{print $1}')"
      ;;
    kind)
      current="$(kind version | awk '{print $2}')"
      ;;
    docker)
      current="$(docker version --format '{{.Client.Version}}')"
      ;;
    jq)
      current="$(jq --version | cut -d- -f2)"
      ;;
    *)
      echo "Unsupported tool for version check: $tool" >&2
      exit 1
      ;;
  esac

  current="$(normalize_version "$current")"
  required="$(normalize_version "$required")"

  if [[ "$(printf '%s\n%s\n' "$required" "$current" | sort -V | head -n1)" != "$required" ]]; then
    echo "Required $tool >= $required, found $current" >&2
    exit 1
  fi

  echo "$tool $current (>= $required) OK"
}

main() {
  if [[ ! -f "$KIND_CONFIG" ]]; then
    echo "Kind config not found at $KIND_CONFIG" >&2
    exit 1
  fi

  for tool in "${!REQUIRED_VERSIONS[@]}"; do
    require_tool "$tool"
    ensure_minimum_version "$tool"
  done

  echo "Deleting existing Kind cluster (if any): ${CLUSTER_NAME}"
  kind delete cluster --name "${CLUSTER_NAME}" || true

  echo "Creating Kind cluster ${CLUSTER_NAME} using ${KIND_CONFIG}"
  kind create cluster --name "${CLUSTER_NAME}" --config "${KIND_CONFIG}"

  local context="kind-${CLUSTER_NAME}"
  echo "Switching kubectl context to ${context}"
  kubectl config use-context "${context}" >/dev/null

  echo "Kind cluster ${CLUSTER_NAME} ready."
}

main "$@"
