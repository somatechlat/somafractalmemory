#!/usr/bin/env bash
set -euo pipefail

log() { echo "[ENTRYPOINT] $(date -u +'%Y-%m-%dT%H:%M:%SZ') $*"; }

APP_MODULE=${UVICORN_APP:-examples.api:app}
HOST=${UVICORN_HOST:-0.0.0.0}
PORT=${UVICORN_PORT:-9595}
WORKERS=${UVICORN_WORKERS:-4}
BACKLOG=${UVICORN_BACKLOG:-2048}
KEEP_ALIVE=${UVICORN_TIMEOUT_KEEP_ALIVE:-30}
GRACEFUL=${UVICORN_TIMEOUT_GRACEFUL:-60}
EXTRA_ARGS=${UVICORN_EXTRA_ARGS:-}

# Fast start mode: skip heavy model downloads & reduce workers to 1 (overridable)
FAST_START=${SOMA_FAST_START:-1}
if [[ "$FAST_START" == "1" || "$FAST_START" == "true" ]]; then
  export SOMA_FORCE_HASH_EMBEDDINGS=1
  if [[ "${UVICORN_WORKERS:-}" == "" || "$UVICORN_WORKERS" == "4" ]]; then
    WORKERS=1
  fi
  log "Fast start enabled (SOMA_FAST_START=1): forcing hash embeddings + workers=$WORKERS"
fi

# Optional dependency wait (defaults on). Disable with SOMA_SKIP_DEP_WAIT=1
if [[ "${SOMA_SKIP_DEP_WAIT:-0}" != "1" ]]; then
  WAIT_HOSTS=("${REDIS_HOST:-redis}:$(echo ${REDIS_PORT:-6379})" \
             "${QDRANT_HOST:-qdrant}:$(echo ${QDRANT_PORT:-6333})" )
  if [[ -n "${POSTGRES_URL:-}" ]]; then
    # Extract host:port from postgres URL
    pg_host_port=$(echo "$POSTGRES_URL" | sed -E 's#.*://[^@]*@([^/:]+):?([0-9]+)?.*#\1:\2#')
    if [[ "$pg_host_port" != *":" ]]; then
      pg_host_port="$pg_host_port:5432"
    fi
    WAIT_HOSTS+=("$pg_host_port")
  fi
  if [[ -n "${KAFKA_BOOTSTRAP_SERVERS:-}" ]]; then
    # Only take first broker
    first_broker=${KAFKA_BOOTSTRAP_SERVERS%%,*}
    WAIT_HOSTS+=("$first_broker")
  fi
  for hp in "${WAIT_HOSTS[@]}"; do
    host=${hp%%:*}; port=${hp##*:}
    [[ -z "$host" || -z "$port" ]] && continue
    log "Waiting for $host:$port ..."
    for i in $(seq 1 40); do
      if nc -z "$host" "$port" 2>/dev/null; then
        log "Service $host:$port reachable (attempt $i)"; break
      fi
      sleep 0.75
      if [[ $i -eq 40 ]]; then
        log "WARNING: Timeout waiting for $host:$port (continuing anyway)"
      fi
    done
  done
else
  log "Skipping dependency wait (SOMA_SKIP_DEP_WAIT=1)"
fi

log "Starting uvicorn app=$APP_MODULE host=$HOST port=$PORT workers=$WORKERS"
if [[ "${START_ASYNC_GRPC:-0}" == "1" ]]; then
  log "Starting async gRPC server"
  exec python -m somafractalmemory.async_grpc_server
else
  exec uvicorn "$APP_MODULE" \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --backlog "$BACKLOG" \
    --timeout-keep-alive "$KEEP_ALIVE" \
    --timeout-graceful-shutdown "$GRACEFUL" \
    $EXTRA_ARGS
fi
