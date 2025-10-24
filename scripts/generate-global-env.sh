#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/generate-global-env.sh <mode> [output_path]
# Modes: dev_full | dev_prod | prod | prod_ha
# Default output path: $GITHUB_WORKSPACE/.ci/soma-global.env (or ./\.ci/soma-global.env)

MODE=${1:-dev_full}
OUT_PATH=${2:-}

if [[ -z "${OUT_PATH}" ]]; then
  if [[ -n "${GITHUB_WORKSPACE:-}" ]]; then
    OUT_PATH="$GITHUB_WORKSPACE/.ci/soma-global.env"
  else
    OUT_PATH=".ci/soma-global.env"
  fi
fi

mkdir -p "$(dirname "$OUT_PATH")"

bool() {
  case "$1" in
    true|True|TRUE|1|yes|on) echo true ;;
    false|False|FALSE|0|no|off) echo false ;;
    *) echo "$1" ;;
  esac
}

case "$MODE" in
  dev_full)
    JWT=$(bool false); OPA=$(bool false); MTLS=$(bool false); EMB=$(bool false); INF=$(bool false); REPL=1; ISTIO=$(bool false); VAULT=$(bool false) ;;
  dev_prod)
    JWT=$(bool true);  OPA=$(bool true);  MTLS=$(bool true);  EMB=$(bool true);  INF=$(bool true);  REPL=1; ISTIO=$(bool true);  VAULT=$(bool true)  ;;
  prod)
    JWT=$(bool true);  OPA=$(bool true);  MTLS=$(bool true);  EMB=$(bool true);  INF=$(bool true);  REPL=2; ISTIO=$(bool true);  VAULT=$(bool true)  ;;
  prod_ha)
    JWT=$(bool true);  OPA=$(bool true);  MTLS=$(bool true);  EMB=$(bool true);  INF=$(bool true);  REPL=3; ISTIO=$(bool true);  VAULT=$(bool true)  ;;
  *) echo "Unsupported mode: $MODE" >&2; exit 1 ;;
esac

cat > "$OUT_PATH" <<EOF
# Unified global env – mode: $MODE
DEPLOY_MODE=$MODE
JWT_ENABLED=$JWT
OPA_ENABLED=$OPA
MTLS_ENABLED=$MTLS
ENABLE_REAL_EMBEDDINGS=$EMB
USE_REAL_INFRA=$INF
REPLICA_COUNT=$REPL
CPU_REQUEST=100m
CPU_LIMIT=200m
MEM_REQUEST=128Mi
MEM_LIMIT=256Mi
ISTIO_INJECTION=$ISTIO
VAULT_AGENT_INJECT=$VAULT
POSTGRES_PORT=5432
REDIS_PORT=6379
QDRANT_PORT=6333
KAFKA_PORT=9092
API_PORT=9595
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=somamemory
PROMETHEUS_SCRAPE=true
OTEL_ENABLED=true
EOF

echo "✅ Global env generated at $OUT_PATH for mode '$MODE'"
