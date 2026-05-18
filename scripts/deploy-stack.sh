#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# SomaStack — Unified Deployment Script
# Brings up SomaFractalMemory + SomaBrain with health-check orchestration.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STACK_DIR="${STACK_DIR:-${REPO_ROOT}/../soma-stack}"
COMPOSE_FILE="${COMPOSE_FILE:-${STACK_DIR}/docker-compose.soma-stack.yml}"
ENV_FILE="${ENV_FILE:-${STACK_DIR}/.env.soma-stack}"

SFM_HEALTH_URL="${SOMA_HEALTH_URL:-http://localhost:10101/healthz}"
BRAIN_HEALTH_URL="${BRAIN_HEALTH_URL:-http://localhost:30101/health}"
SFM_API_TOKEN="${SOMA_API_TOKEN:-}"

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --down      Tear down the entire soma-stack.
  --logs      Tail logs from all services (follow mode).
  --help      Show this help message.

Environment:
  STACK_DIR       Directory containing docker-compose.soma-stack.yml
                  (default: ${REPO_ROOT}/../soma-stack)
  COMPOSE_FILE    Override compose file path.
  ENV_FILE        Override env file path.
EOF
}

# ── Prerequisites ─────────────────────────────────────────────────────────────
check_prerequisites() {
  log_info "Checking prerequisites..."

  if ! command -v docker >/dev/null 2>&1; then
    log_error "Docker is not installed or not in PATH."
    exit 1
  fi

  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
  else
    log_error "Docker Compose is not installed."
    exit 1
  fi

  if [[ ! -f "$COMPOSE_FILE" ]]; then
    log_error "Compose file not found: $COMPOSE_FILE"
    exit 1
  fi

  log_info "Using compose command: $COMPOSE_CMD"
  log_info "Using compose file:  $COMPOSE_FILE"
}

# ── Tear down ─────────────────────────────────────────────────────────────────
stack_down() {
  log_info "Tearing down soma-stack..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --volumes --remove-orphans
  log_info "Stack torn down."
}

# ── Tail logs ─────────────────────────────────────────────────────────────────
stack_logs() {
  log_info "Tailing logs (Ctrl+C to exit)..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
}

# ── Wait for HTTP health ──────────────────────────────────────────────────────
wait_for_http() {
  local url="$1"
  local name="$2"
  local max_attempts="${3:-60}"
  local attempt=0

  log_info "Waiting for $name to become healthy at $url ..."
  while ! curl -fsS "$url" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [[ $attempt -ge $max_attempts ]]; then
      log_error "$name did not become healthy within $max_attempts attempts."
      return 1
    fi
    sleep 2
  done
  log_info "$name is healthy."
}

# ── Verify cross-stack communication ──────────────────────────────────────────
verify_cross_stack() {
  log_info "Verifying cross-stack communication (Brain → SFM)..."

  # Ask Brain's health endpoint if memory component is reachable
  local brain_health
  brain_health=$(curl -fsS "$BRAIN_HEALTH_URL" 2>/dev/null || echo '{}')

  if echo "$brain_health" | grep -q '"ok": true'; then
    log_info "Brain reports healthy and memory is reachable."
  else
    log_warn "Brain health response did not confirm memory reachability."
    log_warn "Response: $brain_health"
  fi

  # Directly probe SFM from the Brain container
  if docker exec somabrain-standalone-app curl -fsS \
       -H "Authorization: Bearer ${SFM_API_TOKEN}" \
       http://somafractalmemory-standalone-api:10101/healthz >/dev/null 2>&1; then
    log_info "Brain container can reach SFM API directly."
  else
    log_warn "Could not verify direct container-to-container reachability."
    log_warn "(This may be OK if containers are still starting.)"
  fi
}

# ── Deploy ────────────────────────────────────────────────────────────────────
stack_up() {
  log_info "Starting SomaStack deployment..."

  # 1. Pull / build images
  log_info "Pulling / building images..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

  # 2. Bring up SFM infrastructure first
  log_info "Starting SomaFractalMemory infrastructure..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d \
    somafractalmemory-standalone-redis \
    somafractalmemory-standalone-vault \
    somafractalmemory-standalone-postgres \
    somafractalmemory-standalone-opa \
    somafractalmemory-standalone-etcd \
    somafractalmemory-standalone-minio

  # 3. Wait for SFM vault-init to complete, then bring up Milvus + API
  log_info "Waiting for SFM Vault init..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d \
    somafractalmemory-standalone-vault-init

  # Wait for vault-init completion
  local v_attempt=0
  while [[ $(docker inspect -f '{{.State.Status}}' somafractalmemory-standalone-vault-init 2>/dev/null) != "exited" ]]; do
    v_attempt=$((v_attempt + 1))
    if [[ $v_attempt -gt 60 ]]; then
      log_error "SFM vault-init did not complete in time."
      exit 1
    fi
    sleep 1
  done

  # Check exit code
  if [[ $(docker inspect -f '{{.State.ExitCode}}' somafractalmemory-standalone-vault-init 2>/dev/null) != "0" ]]; then
    log_error "SFM vault-init failed. Check logs:"
    $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs somafractalmemory-standalone-vault-init
    exit 1
  fi

  # 4. Bring up Milvus and SFM API
  log_info "Starting SFM Milvus and API..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d \
    somafractalmemory-standalone-milvus \
    somafractalmemory-standalone-api

  # 5. Wait for SFM API health
  wait_for_http "$SFM_HEALTH_URL" "SomaFractalMemory API"

  # 6. Bring up Brain infrastructure
  log_info "Starting SomaBrain infrastructure..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d \
    somabrain-standalone-redis \
    somabrain-standalone-kafka \
    somabrain-standalone-opa \
    somabrain-standalone-prometheus \
    somabrain-standalone-jaeger \
    somabrain-standalone-postgres \
    somabrain-standalone-vault

  # 7. Wait for Brain vault-init
  log_info "Waiting for Brain Vault init..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d \
    somabrain-standalone-vault-init

  local bv_attempt=0
  while [[ $(docker inspect -f '{{.State.Status}}' somabrain-standalone-vault-init 2>/dev/null) != "exited" ]]; do
    bv_attempt=$((bv_attempt + 1))
    if [[ $bv_attempt -gt 60 ]]; then
      log_error "Brain vault-init did not complete in time."
      exit 1
    fi
    sleep 1
  done

  if [[ $(docker inspect -f '{{.State.ExitCode}}' somabrain-standalone-vault-init 2>/dev/null) != "0" ]]; then
    log_error "Brain vault-init failed. Check logs:"
    $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs somabrain-standalone-vault-init
    exit 1
  fi

  # 8. Bring up remaining Brain services
  log_info "Starting SomaBrain application services..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d \
    somabrain-standalone-kafka-exporter \
    somabrain-standalone-schema-registry \
    somabrain-standalone-postgres-exporter \
    somabrain-standalone-app \
    somabrain-standalone-cog \
    somabrain-standalone-outbox-publisher \
    somabrain-standalone-integrator-triplet

  # 9. Wait for Brain API health
  wait_for_http "$BRAIN_HEALTH_URL" "SomaBrain API"

  # 10. Cross-stack verification
  verify_cross_stack

  log_info "═══════════════════════════════════════════════════════════════"
  log_info " SomaStack is UP and healthy."
  log_info "  • SomaFractalMemory API: http://localhost:10101"
  log_info "  • SomaBrain API:         http://localhost:30101"
  log_info "═══════════════════════════════════════════════════════════════"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  case "${1:-}" in
    --down)
      check_prerequisites
      stack_down
      ;;
    --logs)
      check_prerequisites
      stack_logs
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    "")
      check_prerequisites
      stack_up
      ;;
    *)
      log_error "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
}

main "$@"
