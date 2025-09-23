#!/usr/bin/env bash
# Start the local stack depending on the chosen mode.
# Usage: ./scripts/start_stack.sh <mode> [--pull] [--with-broker]
# Modes:
#  - development: bring up local services (Postgres + Qdrant). Add --with-broker to include Redpanda+Apicurio.
#  - test: no services (tests use in-memory or mocks).
#  - evented_enterprise, cloud_managed: bring up full evented stack (Redpanda + Apicurio + Postgres + Qdrant).

set -euo pipefail

MODE=${1:-development}
PULL=false
WITH_BROKER=false

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull)
      PULL=true; shift;;
    --with-broker)
      WITH_BROKER=true; shift;;
    *) echo "Unknown flag: $1"; exit 1;;
  esac
done

COMPOSE_FILE="docker-compose.dev.yml"

echo "Selected mode: $MODE"

if [[ "$MODE" == "test" ]]; then
  echo "Test mode: no external services will be started."
  exit 0
fi

if [[ "$PULL" == "true" ]]; then
  echo "Pulling images defined in $COMPOSE_FILE..."
  docker compose -f "$COMPOSE_FILE" pull
fi

if [[ "$MODE" == "development" ]]; then
  echo "Bringing up local dev services: Postgres + Qdrant"
  # Start minimal services for fast local dev
  docker compose -f "$COMPOSE_FILE" up -d postgres qdrant
  if [[ "$WITH_BROKER" == "true" ]]; then
    echo "Also starting broker & registry (Redpanda + Apicurio) as requested"
    docker compose -f "$COMPOSE_FILE" up -d redpanda apicurio
  fi
  echo "Services are starting. Use 'docker compose ps' to check status."
  exit 0
fi

if [[ "$MODE" == "evented_enterprise" || "$MODE" == "cloud_managed" ]]; then
  echo "Bringing up full evented stack: Redpanda + Apicurio + Postgres + Qdrant"
  docker compose -f "$COMPOSE_FILE" up -d redpanda apicurio postgres qdrant
  echo "Full stack is starting. Wait a moment for services to become healthy."
  exit 0
fi

echo "Unsupported mode: $MODE"
exit 2
