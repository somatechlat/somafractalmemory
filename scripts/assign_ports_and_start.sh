#!/usr/bin/env bash
# Find free host ports and write them to .env, then start docker compose services
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

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

check_port_in_use() {
  local port=$1
  if lsof -ti:$port >/dev/null 2>&1; then
    return 0  # port in use
  else
    return 1  # port free
  fi
}

# Get current ports from env or defaults, check for conflicts
REDIS_PORT=${REDIS_HOST_PORT:-6380}
POSTGRES_PORT=${POSTGRES_HOST_PORT:-5434}
QDRANT_PORT=${QDRANT_HOST_PORT:-6333}
KAFKA_HOST_PORT=${KAFKA_HOST_PORT:-9092}
KAFKA_OUTSIDE_PORT=${KAFKA_OUTSIDE_PORT:-19092}

echo "Checking port conflicts..."

if check_port_in_use $REDIS_PORT; then
  echo "Redis port $REDIS_PORT in use, finding alternative..."
  REDIS_PORT=$(find_free_port)
fi

if check_port_in_use $POSTGRES_PORT; then
  echo "Postgres port $POSTGRES_PORT in use, finding alternative..."
  POSTGRES_PORT=$(find_free_port)
fi

if check_port_in_use $QDRANT_PORT; then
  echo "Qdrant port $QDRANT_PORT in use, finding alternative..."
  QDRANT_PORT=$(find_free_port)
fi

if check_port_in_use $KAFKA_HOST_PORT; then
  echo "Kafka host port $KAFKA_HOST_PORT in use, finding alternative..."
  KAFKA_HOST_PORT=$(find_free_port)
fi

if check_port_in_use $KAFKA_OUTSIDE_PORT; then
  echo "Kafka outside port $KAFKA_OUTSIDE_PORT in use, finding alternative..."
  KAFKA_OUTSIDE_PORT=$(find_free_port)
fi

# Write all port assignments
cat > "$ENV_FILE" <<EOF
# Auto-generated host port mappings for local compose
REDIS_HOST_PORT=$REDIS_PORT
POSTGRES_HOST_PORT=$POSTGRES_PORT
QDRANT_HOST_PORT=$QDRANT_PORT
KAFKA_HOST_PORT=$KAFKA_HOST_PORT
KAFKA_OUTSIDE_PORT=$KAFKA_OUTSIDE_PORT

# Set the compose project (cluster) name
COMPOSE_PROJECT_NAME=somafractalmemory
EOF

echo "Port assignments written to $ENV_FILE:"
echo "  Redis: $REDIS_PORT"
echo "  Postgres: $POSTGRES_PORT"
echo "  Qdrant: $QDRANT_PORT"
echo "  Kafka Host: $KAFKA_HOST_PORT"
echo "  Kafka Outside: $KAFKA_OUTSIDE_PORT"
echo "  Memory API: 9595 (fixed)"

# Start the full evented enterprise stack
echo "Starting evented enterprise stack..."
export COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

docker compose --profile core up -d

echo ""
echo "✅ Evented Enterprise stack started successfully!"
echo ""
echo "🔗 Access points:"
echo "  Memory API: http://localhost:9595"
echo "  Postgres: localhost:$POSTGRES_PORT"
echo "  Redis: localhost:$REDIS_PORT"
echo "  Qdrant: http://localhost:$QDRANT_PORT"
echo "  Kafka: localhost:$KAFKA_HOST_PORT (external: localhost:$KAFKA_OUTSIDE_PORT)"
