#!/usr/bin/env bash
# shellcheck disable=SC2086

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/sharedinfra-health.sh [options]

Aggregate a lightweight health snapshot for the Soma Fractal Memory stack.
Requires kubectl access to the target cluster.

Options:
  -n, --namespace <ns>        Kubernetes namespace (default: ${SFM_NAMESPACE:-soma-memory})
      --context <ctx>         kubectl context (optional)
      --release <name>        Helm release name (default: ${HELM_RELEASE:-soma-memory})
      --postgres-pod <pod>    Pod name running Postgres; runs pg_isready inside it
      --postgres-user <user>  Username for pg_isready (default: ${POSTGRES_USER:-postgres})
      --postgres-db <db>      Database name for pg_isready (default: ${POSTGRES_DB:-somamemory})
      --consumer-pod <pod>    Pod name running the consumer; fetches key Prometheus metrics
      --consumer-port <port>  Consumer metrics port (default: ${CONSUMER_METRICS_PORT:-8001})
      --kafka-topic <topic>   Kafka topic to highlight in metrics output (default: ${KAFKA_TOPIC:-memory.events})
      --kafka-group <group>   Kafka consumer group name (default: ${KAFKA_GROUP:-soma-consumer-group})
  -h, --help                  Show this help message
EOF
}

info() { printf '\n==> %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }

require_value() {
  local opt="$1"
  local value="$2"
  if [[ -z "$value" ]]; then
    warn "Option '$opt' requires an argument"; usage; exit 1
  fi
}

NAMESPACE=${SFM_NAMESPACE:-soma-memory}
KUBE_CONTEXT=""
RELEASE=${HELM_RELEASE:-soma-memory}
POSTGRES_POD=""
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DB=${POSTGRES_DB:-somamemory}
CONSUMER_POD=""
CONSUMER_PORT=${CONSUMER_METRICS_PORT:-8001}
KAFKA_TOPIC=${KAFKA_TOPIC:-memory.events}
KAFKA_GROUP=${KAFKA_GROUP:-soma-consumer-group}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--namespace)
      value="${2-}"
      require_value "$1" "$value"
      NAMESPACE="$value"
      shift 2
      ;;
    --context)
      value="${2-}"
      require_value "$1" "$value"
      KUBE_CONTEXT="$value"
      shift 2
      ;;
    --release)
      value="${2-}"
      require_value "$1" "$value"
      RELEASE="$value"
      shift 2
      ;;
    --postgres-pod)
      value="${2-}"
      require_value "$1" "$value"
      POSTGRES_POD="$value"
      shift 2
      ;;
    --postgres-user)
      value="${2-}"
      require_value "$1" "$value"
      POSTGRES_USER="$value"
      shift 2
      ;;
    --postgres-db)
      value="${2-}"
      require_value "$1" "$value"
      POSTGRES_DB="$value"
      shift 2
      ;;
    --consumer-pod)
      value="${2-}"
      require_value "$1" "$value"
      CONSUMER_POD="$value"
      shift 2
      ;;
    --consumer-port)
      value="${2-}"
      require_value "$1" "$value"
      CONSUMER_PORT="$value"
      shift 2
      ;;
    --kafka-topic)
      value="${2-}"
      require_value "$1" "$value"
      KAFKA_TOPIC="$value"
      shift 2
      ;;
    --kafka-group)
      value="${2-}"
      require_value "$1" "$value"
      KAFKA_GROUP="$value"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      warn "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if ! command -v kubectl >/dev/null 2>&1; then
  warn "kubectl not found in PATH"
  exit 1
fi

kubectl_base=(kubectl)
if [[ -n "$KUBE_CONTEXT" ]]; then
  kubectl_base+=(--context "$KUBE_CONTEXT")
fi
kubectl_ns=("${kubectl_base[@]}" -n "$NAMESPACE")

k_base() { "${kubectl_base[@]}" "$@"; }
k_ns() { "${kubectl_ns[@]}" "$@"; }

has_resource() {
  local resource="$1"
  k_base api-resources --names-only 2>/dev/null | grep -Fxq "$resource"
}

info "Cluster snapshot for namespace '$NAMESPACE'"

if command -v helm >/dev/null 2>&1; then
  info "Helm release: $RELEASE"
  if ! helm status "$RELEASE" --namespace "$NAMESPACE" >/dev/null 2>&1; then
    warn "Helm release '$RELEASE' not found"
  else
    helm status "$RELEASE" --namespace "$NAMESPACE"
  fi
fi

info "Pods"
k_ns get pods -o wide || warn "Unable to list pods"

info "Deployments"
k_ns get deploy || warn "Unable to list deployments"

info "StatefulSets"
if ! k_ns get statefulset >/dev/null 2>&1; then
  warn "No statefulsets found or access denied"
else
  k_ns get statefulset
fi

info "PVCs"
k_ns get pvc || warn "Unable to list PVCs"

info "CronJobs"
if ! k_ns get cronjob >/dev/null 2>&1; then
  warn "No CronJobs found"
else
  k_ns get cronjob
fi

if has_resource externalsecrets; then
  info "ExternalSecrets"
  if ! k_ns get externalsecret >/dev/null 2>&1; then
    warn "ExternalSecrets CRD present but no resources listed"
  else
    k_ns get externalsecret
  fi
fi

if has_resource servicemonitors; then
  info "ServiceMonitors"
  k_ns get servicemonitor || warn "Unable to list ServiceMonitors"
fi

if [[ -n "$POSTGRES_POD" ]]; then
  info "Postgres readiness ($POSTGRES_POD)"
  if ! k_ns exec "$POSTGRES_POD" -- pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
    warn "pg_isready reported issues for $POSTGRES_POD"
  fi
fi

if [[ -n "$CONSUMER_POD" ]]; then
  info "Consumer metrics snapshot ($CONSUMER_POD)"
  python_bin=python3
  if ! k_ns exec "$CONSUMER_POD" -- sh -c 'command -v python3 >/dev/null 2>&1'; then
    python_bin=python
  fi
  if ! k_ns exec "$CONSUMER_POD" -- "$python_bin" - <<PY; then
import sys
import urllib.request
PORT = int(${CONSUMER_PORT})
PROM_FILTERS = (
    "consumer_messages_consumed_total",
    "consumer_process_failure_total",
    "consumer_processing_latency_seconds_sum",
    "consumer_processing_latency_seconds_count",
)

def main() -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/metrics", timeout=3) as handle:
            data = handle.read().decode()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"metrics scrape failed: {exc}")
        return 1

    matched = [line for line in data.splitlines() if line.startswith(PROM_FILTERS)]
    if not matched:
        print("no matching consumer metrics found")
        return 1

    for line in matched:
        print(line)
    return 0

raise SystemExit(main())
PY
  then
    warn "Failed to scrape consumer metrics"
  fi
fi

info "Recent events"
if ! k_ns get events --sort-by=.lastTimestamp --tail=10 >/dev/null 2>&1; then
  warn "Unable to read events"
else
  k_ns get events --sort-by=.lastTimestamp --tail=10
fi

info "Hint"
echo "Consider port-forwarding Prometheus or running 'kubectl port-forward' to query metrics directly."
