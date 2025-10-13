#!/usr/bin/env bash
# Reset local Docker-based shared infrastructure stacks to a clean state.
# This mirrors the SomaStack Shared Infra playbook reset flow for compose users.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_COMPOSE_FILES=(
  "docker-compose.yml"
  "docker-compose.test.yml"
  "docker-compose.dev.yml"
)

COMPOSE_FILES=()
for f in "${DEFAULT_COMPOSE_FILES[@]}"; do
  if [[ -f "${REPO_ROOT}/${f}" ]]; then
    COMPOSE_FILES+=("${REPO_ROOT}/${f}")
  fi
done

if [[ ${#COMPOSE_FILES[@]} -eq 0 ]]; then
  echo "No compose files found. Nothing to reset." >&2
  exit 0
fi

echo "Stopping compose stacks..."
for compose_file in "${COMPOSE_FILES[@]}"; do
  services="$(docker compose -f "${compose_file}" config --services 2>/dev/null || true)"
  if [[ -z "${services}" ]]; then
    echo "  skipping ${compose_file} (no services resolved)"
    continue
  fi
  echo "  docker compose -f ${compose_file} down"
  docker compose -f "${compose_file}" down || true
done

# Named volumes to remove (both primary and test stacks).
VOLUMES=(
  # Primary stack volumes (canonical compose now uses somafractalmemory_ prefixes)
  somafractalmemory_postgres_data
  somafractalmemory_redis_data
  somafractalmemory_kafka_data
  somafractalmemory_qdrant_data
  somafractalmemory_prometheus_data
  somafractalmemory_grafana_data
  somafractalmemory_vault_data
  somafractalmemory_etcd_data
  somafractalmemory_quadrant_data
  # Test/legacy volumes
  postgres_test_data
  redis_test_data
  kafka_test_data
  qdrant_test_storage
  postgres_data
  redis_data
  kafka_data
  qdrant_storage
)

echo "Removing Docker volumes (if present)..."
for volume in "${VOLUMES[@]}"; do
  if docker volume inspect "${volume}" >/dev/null 2>&1; then
    echo "  docker volume rm ${volume}"
    docker volume rm "${volume}" || true
  fi
done

cat <<'EOF'
Docker shared infra reset complete.

Next steps:
  - docker compose up -d redis postgres qdrant kafka   # local baseline
  - or scripts/start_stack.sh evented_enterprise
EOF
