#!/usr/bin/env bash
# Pull and load container images required for the Soma shared infra Kind cluster.

set -euo pipefail

CLUSTER_NAME="${KIND_CLUSTER_NAME:-soma}"

IMAGES=(
  "bitnamilegacy/postgresql-repmgr:16.6.0-debian-12-r3"
  "bitnamilegacy/pgpool:4.6.3-debian-12-r0"
  "apache/kafka:3.8.0"
  "redis:7.2.4-alpine"
  "hashicorp/vault:1.15.4"
  "openpolicyagent/opa:0.57.0-debug"
  "prom/prometheus:v2.47.2"
  "grafana/grafana:10.2.3"
)

require_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required tool: $1" >&2
    exit 1
  fi
}

main() {
  require_tool docker
  require_tool kind

  for image in "${IMAGES[@]}"; do
    echo "Pulling ${image}"
    docker pull "${image}"
    echo "Loading ${image} into Kind cluster ${CLUSTER_NAME}"
    kind load docker-image "${image}" --name "${CLUSTER_NAME}"
  done

  echo "Image preload complete."
}

main "$@"
