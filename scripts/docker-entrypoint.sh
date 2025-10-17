#!/usr/bin/env bash
set -euo pipefail

# Minimal entrypoint for local development
# - waits for dependent services to be reachable
# - runs database migrations if alembic present
# - launches uvicorn with configurable workers

ROOT_DIR="/app"
UV_WORKERS=${UVICORN_WORKERS:-2}
UV_TIMEOUT_GRACEFUL=${UVICORN_TIMEOUT_GRACEFUL:-60}
UV_TIMEOUT_KEEP_ALIVE=${UVICORN_TIMEOUT_KEEP_ALIVE:-30}

wait_for() {
  local hostport="$1"
  local retries=30
  local wait=2
  local i=0
  local host=$(echo "$hostport" | cut -d: -f1)
  local port=$(echo "$hostport" | cut -d: -f2)
  until nc -z "$host" "$port"; do
    i=$((i+1))
    if [ "$i" -ge "$retries" ]; then
      echo "Timeout waiting for $hostport"
      return 1
    fi
    sleep $wait
  done
}

echo "Starting entrypoint: waiting for dependencies"
# default service endpoints (can be overridden via env)
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}
QDRANT_HOST=${QDRANT_HOST:-qdrant}
QDRANT_PORT=${QDRANT_PORT:-6333}

wait_for "${POSTGRES_HOST}:${POSTGRES_PORT}"
wait_for "${REDIS_HOST}:${REDIS_PORT}"
wait_for "${QDRANT_HOST}:${QDRANT_PORT}"

cd ${ROOT_DIR}

# Run alembic migrations if present
if [ -d "alembic" ] && command -v alembic >/dev/null 2>&1; then
  echo "Running alembic upgrade head"
  alembic upgrade head || echo "alembic upgrade failed; continuing"
fi

echo "Launching memory API with uvicorn (workers=$UV_WORKERS)"
# Note: not all uvicorn builds support --graceful-timeout. Use safe flags.
exec uvicorn somafractalmemory.http_api:app \
  --host 0.0.0.0 --port 9595 \
  --workers ${UV_WORKERS} \
  --timeout-keep-alive ${UV_TIMEOUT_KEEP_ALIVE} \
  --log-level info
