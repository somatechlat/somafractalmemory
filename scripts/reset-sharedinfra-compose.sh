#!/usr/bin/env bash
# Reset local Docker-based shared infrastructure stacks to a clean state.
# This mirrors the SomaStack Shared Infra playbook reset flow for compose users.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Use single consolidated docker-compose.yml with all profiles
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Compose file ${COMPOSE_FILE} not found. Nothing to reset." >&2
  exit 0
fi

echo "Stopping all compose stacks (all profiles)..."
echo "  docker compose -f ${COMPOSE_FILE} --profile core --profile dev --profile test --profile monitoring --profile ops --profile proxy down"
docker compose -f "${COMPOSE_FILE}" --profile core --profile dev --profile test --profile monitoring --profile ops --profile proxy down || true

# Named volumes to remove (from consolidated docker-compose.yml)
VOLUMES=(
  # Primary stack volumes (sfm_ prefix from docker-compose.yml)
  sfm_postgres_data
  sfm_redis_data
  sfm_kafka_data
  sfm_qdrant_data
  sfm_prometheus_data
  sfm_grafana_data
  sfm_vault_data
  sfm_etcd_data
  sfm_quadrant_data
  # Test environment volumes
  postgres_test_data
  redis_test_data
  kafka_test_data
  qdrant_test_storage
  # Legacy volumes (cleanup)
  somafractalmemory_postgres_data
  somafractalmemory_redis_data
  somafractalmemory_kafka_data
  somafractalmemory_qdrant_data
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
  - docker compose --profile core up -d               # Core stack (API + infrastructure)
  - docker compose --profile dev up -d                # Development with volume mounts
  - docker compose --profile test up -d               # Test environment (port 9999)
  - ./scripts/assign_ports_and_start.sh               # Auto-assign ports and start
EOF
