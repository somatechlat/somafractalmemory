#!/usr/bin/env bash
# Find free host ports and write them to .env, then start docker compose services
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.auto"

find_free_port() {
  # let the OS pick a free port by binding a socket to port 0
  python3 - <<'PY'
import socket
s=socket.socket()
s.bind(('127.0.0.1',0))
print(s.getsockname()[1])
s.close()
PY
}

REDIS_PORT=${REDIS_HOST_PORT:-}
POSTGRES_PORT=${POSTGRES_HOST_PORT:-}
QDRANT_PORT=${QDRANT_HOST_PORT:-}

if [ -z "$REDIS_PORT" ]; then
  REDIS_PORT=$(find_free_port)
fi
if [ -z "$POSTGRES_PORT" ]; then
  POSTGRES_PORT=$(find_free_port)
fi
if [ -z "$QDRANT_PORT" ]; then
  QDRANT_PORT=$(find_free_port)
fi

cat > "$ENV_FILE" <<EOF
# Auto-generated host port mappings for local compose
REDIS_HOST_PORT=$REDIS_PORT
POSTGRES_HOST_PORT=$POSTGRES_PORT
QDRANT_HOST_PORT=$QDRANT_PORT
EOF

echo wrote $ENV_FILE

echo "Starting docker compose with host ports: redis=$REDIS_PORT, postgres=$POSTGRES_PORT, qdrant=$QDRANT_PORT"
export COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
# use env_file override by copying to .env for compose
cp "$ENV_FILE" "$ROOT_DIR/.env"

docker compose up -d redis postgres qdrant

echo "Services started"

echo "Please set USE_REAL_INFRA=1 and run pytest as needed."
