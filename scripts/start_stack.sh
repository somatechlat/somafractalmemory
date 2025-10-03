#!/usr/bin/env bash
# Start the local stack depending on the chosen mode.
# Usage: ./scripts/start_stack.sh <mode> [--pull] [--with-broker]
# Modes:
#  - development: bring up local services (Postgres + Qdrant). Add --with-broker to include the Kafka broker (legacy flag originally started Redpanda+Apicurio).
#  - test: no services (tests use in-memory or ephemeral paths).
#  - evented_enterprise, cloud_managed: bring up full evented stack (Kafka broker + Postgres + Qdrant). Legacy docs may still reference Redpanda/Apicurio.

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
# Fallback: if the dev compose file does not exist (current repo layout), use primary docker-compose.yml
if [[ ! -f "$COMPOSE_FILE" ]]; then
  COMPOSE_FILE="docker-compose.yml"
fi

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
    echo "Also starting broker (Kafka) as requested via legacy --with-broker flag"
    # Backward compatibility: if compose still defines redpanda/apicurio, start them; otherwise start kafka
    if docker compose -f "$COMPOSE_FILE" config --services | grep -q '^kafka$'; then
      docker compose -f "$COMPOSE_FILE" up -d kafka
    else
      docker compose -f "$COMPOSE_FILE" up -d redpanda apicurio || true
    fi
  fi
  echo "Services are starting. Use 'docker compose ps' to check status."
  exit 0
fi

if [[ "$MODE" == "evented_enterprise" || "$MODE" == "cloud_managed" ]]; then
  echo "Bringing up full evented stack: Kafka broker + Postgres + Qdrant (legacy Redpanda/Apicurio if present)"
  if docker compose -f "$COMPOSE_FILE" config --services | grep -q '^kafka$'; then
    docker compose -f "$COMPOSE_FILE" up -d kafka postgres qdrant
  else
    docker compose -f "$COMPOSE_FILE" up -d redpanda apicurio postgres qdrant || true
  fi
  echo "Full stack is starting. Wait a moment for services to become healthy."
  exit 0
fi

echo "Unsupported mode: $MODE"
exit 2
