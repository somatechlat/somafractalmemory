#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# SomaStack — Health & Integration Verification Script
# Checks all services, APIs, and cross-stack memory communication.
# ═══════════════════════════════════════════════════════════════════════════════

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SFM_API_URL="${SFM_API_URL:-http://localhost:10101}"
BRAIN_API_URL="${BRAIN_API_URL:-http://localhost:30101}"
SFM_API_TOKEN="${SFM_API_TOKEN:-${SOMA_API_TOKEN:-}}"
BRAIN_MEMORY_TOKEN="${BRAIN_MEMORY_TOKEN:-${SOMABRAIN_MEMORY_HTTP_TOKEN:-}}"

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

log_pass()   { echo -e "${GREEN}[PASS]${NC} $*"; ((PASS++)); }
log_fail()   { echo -e "${RED}[FAIL]${NC} $*"; ((FAIL++)); }
log_info()   { echo -e "${BLUE}[INFO]${NC} $*"; }
log_warn()   { echo -e "${YELLOW}[WARN]${NC} $*"; }

# ── Check Docker containers are running ───────────────────────────────────────
check_containers() {
  log_info "Checking running containers..."

  local expected=(
    somafractalmemory-standalone-redis
    somafractalmemory-standalone-vault
    somafractalmemory-standalone-postgres
    somafractalmemory-standalone-opa
    somafractalmemory-standalone-etcd
    somafractalmemory-standalone-minio
    somafractalmemory-standalone-milvus
    somafractalmemory-standalone-api
    somabrain-standalone-redis
    somabrain-standalone-kafka
    somabrain-standalone-opa
    somabrain-standalone-prometheus
    somabrain-standalone-jaeger
    somabrain-standalone-postgres
    somabrain-standalone-vault
    somabrain-standalone-app
    somabrain-standalone-cog
    somabrain-standalone-outbox-publisher
    somabrain-standalone-integrator-triplet
  )

  for container in "${expected[@]}"; do
    if docker ps --format '{{.Names}}' | grep -qx "$container"; then
      log_pass "Container running: $container"
    else
      log_fail "Container NOT running: $container"
    fi
  done
}

# ── Check SFM API responds ────────────────────────────────────────────────────
check_sfm_api() {
  log_info "Checking SomaFractalMemory API..."

  local response
  response=$(curl -fsS "${SFM_API_URL}/healthz" 2>/dev/null || echo "")

  if [[ -n "$response" ]]; then
    log_pass "SFM API responds at ${SFM_API_URL}/healthz"
    log_info "Response: $response"
  else
    log_fail "SFM API did not respond at ${SFM_API_URL}/healthz"
  fi
}

# ── Check Brain API responds ──────────────────────────────────────────────────
check_brain_api() {
  log_info "Checking SomaBrain API..."

  local response
  response=$(curl -fsS "${BRAIN_API_URL}/health" 2>/dev/null || echo "")

  if [[ -n "$response" ]]; then
    log_pass "Brain API responds at ${BRAIN_API_URL}/health"
    log_info "Response: $response"
  else
    log_fail "Brain API did not respond at ${BRAIN_API_URL}/health"
  fi
}

# ── Check Brain can reach SFM (memory store/recall cycle) ─────────────────────
check_memory_cycle() {
  log_info "Testing memory store/recall cycle via SFM API..."

  if [[ -z "$SFM_API_TOKEN" ]]; then
    log_warn "SFM_API_TOKEN not set — skipping authenticated memory cycle test."
    return
  fi

  local test_coord="verify-stack-$(date +%s)"
  local store_payload
  store_payload=$(cat <<EOF
{"coord": "$test_coord", "payload": {"test": true, "source": "verify-stack"}, "memory_type": "episodic"}
EOF
)

  # Store
  local store_response
  store_response=$(curl -fsS -X POST "${SFM_API_URL}/api/v1/memories" \
    -H "Authorization: Bearer ${SFM_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$store_payload" 2>/dev/null || echo "")

  if [[ -n "$store_response" ]]; then
    log_pass "Memory store succeeded: $store_response"
  else
    log_fail "Memory store failed"
    return
  fi

  # Recall
  local recall_response
  recall_response=$(curl -fsS "${SFM_API_URL}/api/v1/memories/${test_coord}" \
    -H "Authorization: Bearer ${SFM_API_TOKEN}" 2>/dev/null || echo "")

  if [[ -n "$recall_response" ]]; then
    log_pass "Memory recall succeeded: $recall_response"
  else
    log_fail "Memory recall failed"
  fi

  # Cleanup
  curl -fsS -X DELETE "${SFM_API_URL}/api/v1/memories/${test_coord}" \
    -H "Authorization: Bearer ${SFM_API_TOKEN}" >/dev/null 2>&1 || true
}

# ── Check cross-stack reachability from Brain container ───────────────────────
check_brain_to_sfm() {
  log_info "Checking Brain → SFM container reachability..."

  if ! docker ps --format '{{.Names}}' | grep -qx "somabrain-standalone-app"; then
    log_warn "Brain app container not running — skipping container-level check."
    return
  fi

  local token_arg=""
  if [[ -n "$SFM_API_TOKEN" ]]; then
    token_arg="-H \"Authorization: Bearer ${SFM_API_TOKEN}\""
  fi

  if docker exec somabrain-standalone-app sh -c \
       "curl -fsS ${token_arg} http://somafractalmemory-standalone-api:10101/healthz >/dev/null 2>&1"; then
    log_pass "Brain container can reach SFM API internally"
  else
    log_fail "Brain container cannot reach SFM API internally"
  fi
}

# ── Summary ───────────────────────────────────────────────────────────────────
summary() {
  echo ""
  log_info "═══════════════════════════════════════════════════════════════"
  log_info " Verification complete: ${PASS} passed, ${FAIL} failed"
  log_info "═══════════════════════════════════════════════════════════════"

  if [[ $FAIL -gt 0 ]]; then
    exit 1
  fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  echo -e "${BLUE}SomaStack Verification${NC}"
  echo "============================================================"

  check_containers
  check_sfm_api
  check_brain_api
  check_memory_cycle
  check_brain_to_sfm
  summary
}

main "$@"
