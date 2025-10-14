#!/usr/bin/env bash
# Start the local stack for the single supported mode (evented_enterprise).
# Usage: ./scripts/start_stack.sh [evented_enterprise] [--pull]

set -euo pipefail

MODE="evented_enterprise"
PULL=false

if [[ $# -gt 0 && "$1" != --pull ]]; then
  MODE="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull)
      PULL=true; shift;;
    *) echo "Unknown flag: $1"; exit 1;;
  esac
done

if [[ "$MODE" != "evented_enterprise" ]]; then
  echo "Unsupported mode: $MODE (only evented_enterprise is supported)"
  exit 2
fi

# Use the main docker-compose.yml with dev profile for development
COMPOSE_FILE="docker-compose.yml"
PROFILE="--profile dev"

echo "Selected mode: $MODE"

if [[ "$PULL" == "true" ]]; then
  echo "Pulling images defined in $COMPOSE_FILE..."
  docker compose -f "$COMPOSE_FILE" $PROFILE pull
fi

echo "Bringing up full evented stack: Kafka broker + Postgres + Qdrant"
docker compose -f "$COMPOSE_FILE" $PROFILE up -d kafka postgres qdrant
echo "Full stack is starting. Wait a moment for services to become healthy."
