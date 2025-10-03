#!/usr/bin/env bash
set -euo pipefail

APP_MODULE=${UVICORN_APP:-examples.api:app}
HOST=${UVICORN_HOST:-0.0.0.0}
PORT=${UVICORN_PORT:-9595}
WORKERS=${UVICORN_WORKERS:-4}
BACKLOG=${UVICORN_BACKLOG:-2048}
KEEP_ALIVE=${UVICORN_TIMEOUT_KEEP_ALIVE:-30}
GRACEFUL=${UVICORN_TIMEOUT_GRACEFUL:-60}
EXTRA_ARGS=${UVICORN_EXTRA_ARGS:-}

exec uvicorn "$APP_MODULE" \
  --host "$HOST" \
  --port "$PORT" \
  --workers "$WORKERS" \
  --backlog "$BACKLOG" \
  --timeout-keep-alive "$KEEP_ALIVE" \
  --timeout-graceful-shutdown "$GRACEFUL" \
  $EXTRA_ARGS
