#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.development.yml}
PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "Docker Compose project file: $COMPOSE_FILE"
echo "Listing services and their host port bindings:"

docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" ps --services | while read -r svc; do
  echo "Service: $svc"
  docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" ps --service-ports "$svc" || true
  echo "---"
done
