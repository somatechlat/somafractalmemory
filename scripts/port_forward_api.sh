#!/usr/bin/env bash
# Idempotent helper to ensure the API service is port-forwarded to localhost:9595
# Usage: ./scripts/port_forward_api.sh [start|stop|status]

set -euo pipefail

NAMESPACE=${NAMESPACE:-soma-memory}
SERVICE=${SERVICE:-soma-memory-somafractalmemory}
LOCAL_PORT=${LOCAL_PORT:-9595}
REMOTE_PORT=${REMOTE_PORT:-9595}
PF_BASE="port-forward-${SERVICE}-${LOCAL_PORT}"
PF_PIDFILE="/tmp/${PF_BASE}.pid"
PF_LOGFILE="/tmp/${PF_BASE}.log"

start() {
  if [ -f "$PF_PIDFILE" ]; then
    pid=$(cat "$PF_PIDFILE")
    if kill -0 "$pid" 2>/dev/null; then
      echo "Port-forward already running (pid=$pid)"
      exit 0
    else
      echo "Stale pidfile found, removing"
      rm -f "$PF_PIDFILE"
    fi
  fi

  echo "Starting port-forward from service/$SERVICE ($NAMESPACE) $LOCAL_PORT:$REMOTE_PORT"
  # run in background and detach; redirect output to logfile for diagnostics
  nohup kubectl port-forward -n "$NAMESPACE" svc/"$SERVICE" "$LOCAL_PORT":"$REMOTE_PORT" > "$PF_LOGFILE" 2>&1 &
  pf_pid=$!
  echo "$pf_pid" > "$PF_PIDFILE"
  sleep 0.5
  if kill -0 "$pf_pid" 2>/dev/null; then
    echo "Port-forward started (pid=$pf_pid)"
    exit 0
  else
  echo "Failed to start port-forward; check $PF_LOGFILE"
    exit 2
  fi
}

stop() {
  if [ -f "$PF_PIDFILE" ]; then
    pid=$(cat "$PF_PIDFILE")
    echo "Stopping port-forward (pid=$pid)"
    kill "$pid" || true
    rm -f "$PF_PIDFILE"
    exit 0
  else
    echo "No port-forward pidfile found"
    exit 0
  fi
}

status() {
  if [ -f "$PF_PIDFILE" ]; then
    pid=$(cat "$PF_PIDFILE")
    if kill -0 "$pid" 2>/dev/null; then
      echo "Running (pid=$pid)"
      exit 0
    else
      echo "Stale pidfile (pid=$pid)"
      exit 1
    fi
  else
    echo "Not running"
    exit 1
  fi
}

case ${1:-start} in
  start) start ;;
  stop) stop ;;
  status) status ;;
  *) echo "Usage: $0 [start|stop|status]"; exit 2 ;;
esac
