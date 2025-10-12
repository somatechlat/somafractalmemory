#!/usr/bin/env bash
# Reset local Docker-based shared infrastructure stacks to a clean state.
# This mirrors the SomaStack Shared Infra playbook reset flow for compose users.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_COMPOSE_FILES=(
  "docker-compose.yml"
  "docker-compose.test.yml"
  "docker-compose.dev.yml"
  "infra/docker/shared-infra.compose.yaml"
)

mapfile -t COMPOSE_FILES < <(
  for f in "${DEFAULT_COMPOSE_FILES[@]}"; do
    if [[ -f "${REPO_ROOT}/${f}" ]]; then
      printf '%s\n' "${REPO_ROOT}/${f}"
    fi
  done
)

if [[ ${#COMPOSE_FILES[@]} -eq 0 ]]; then
  echo "No compose files found. Nothing to reset." >&2
  exit 0
fi

echo "Stopping compose stacks..."
for compose_file in "${COMPOSE_FILES[@]}"; do
  echo "  docker compose -f ${compose_file} down"
  docker compose -f "${compose_file}" down || true
done

# Named volumes to remove (both primary and test stacks).
VOLUMES=(
  postgres_data
  redis_data
  kafka_data
  qdrant_storage
  postgres_test_data
  redis_test_data
  redpanda_test_data
  qdrant_test_storage
  sharedinfra_postgres-data
  sharedinfra_redis-data
  sharedinfra_kafka-data
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
  - docker compose up -d postgres qdrant kafka   # local baseline
  - or scripts/start_stack.sh development --with-broker
EOF
