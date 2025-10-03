#!/usr/bin/env bash
# Enhanced port forwarding script following Kubernetes best practices
# This implements proper monitoring, health checks, and automatic restarts

set -euo pipefail

NAMESPACE=${NAMESPACE:-soma-memory}
SERVICE=${SERVICE:-soma-memory-somafractalmemory}
LOCAL_PORT=${LOCAL_PORT:-9595}
REMOTE_PORT=${REMOTE_PORT:-9595}
PID_FILE="/tmp/soma-port-forward.pid"
LOG_FILE="/tmp/soma-port-forward.log"
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-30}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

cleanup() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping port-forward (pid=$pid)"
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
}

trap cleanup EXIT INT TERM

check_prerequisites() {
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log "ERROR: Cannot connect to Kubernetes cluster"
        exit 1
    fi

    if ! kubectl get svc "$SERVICE" -n "$NAMESPACE" >/dev/null 2>&1; then
        log "ERROR: Service $SERVICE not found in namespace $NAMESPACE"
        exit 1
    fi
}

start_port_forward() {
    log "Starting reliable port-forward: $SERVICE:$REMOTE_PORT -> localhost:$LOCAL_PORT"

    # Start port-forward in background with logging
    kubectl port-forward -n "$NAMESPACE" "svc/$SERVICE" "$LOCAL_PORT:$REMOTE_PORT" \
        > "$LOG_FILE" 2>&1 &

    local pid=$!
    echo "$pid" > "$PID_FILE"

    # Wait a moment for port-forward to establish
    sleep 2

    if ! kill -0 "$pid" 2>/dev/null; then
        log "ERROR: Port-forward failed to start"
        return 1
    fi

    log "Port-forward started successfully (pid=$pid)"
    return 0
}

health_check() {
    if curl -sf "http://localhost:$LOCAL_PORT/healthz" >/dev/null 2>&1; then
        log "Health check passed"
        return 0
    else
        log "Health check failed"
        return 1
    fi
}

monitor_and_restart() {
    while true; do
        if [[ -f "$PID_FILE" ]]; then
            local pid=$(cat "$PID_FILE")
            if kill -0 "$pid" 2>/dev/null; then
                # Process is running, check health
                if health_check; then
                    log "Port-forward healthy"
                else
                    log "Health check failed, restarting port-forward"
                    cleanup
                    start_port_forward || {
                        log "Failed to restart port-forward, exiting"
                        exit 1
                    }
                fi
            else
                log "Port-forward process died, restarting"
                rm -f "$PID_FILE"
                start_port_forward || {
                    log "Failed to restart port-forward, exiting"
                    exit 1
                }
            fi
        else
            log "PID file missing, starting port-forward"
            start_port_forward || {
                log "Failed to start port-forward, exiting"
                exit 1
            }
        fi

        sleep "$HEALTH_CHECK_INTERVAL"
    done
}

main() {
    case "${1:-start}" in
        start)
            cleanup  # Clean up any existing instances
            check_prerequisites
            start_port_forward
            log "Port-forward established. Use 'curl http://localhost:$LOCAL_PORT/healthz' to test"
            log "Use '$0 monitor' to run with automatic restart monitoring"
            ;;
        monitor)
            cleanup
            check_prerequisites
            start_port_forward
            log "Starting monitoring mode with health checks every ${HEALTH_CHECK_INTERVAL}s"
            monitor_and_restart
            ;;
        stop)
            cleanup
            log "Port-forward stopped"
            ;;
        status)
            if [[ -f "$PID_FILE" ]]; then
                local pid=$(cat "$PID_FILE")
                if kill -0 "$pid" 2>/dev/null; then
                    log "Running (pid=$pid)"
                    health_check && log "Service responding" || log "Service not responding"
                else
                    log "Stale PID file (pid=$pid)"
                    exit 1
                fi
            else
                log "Not running"
                exit 1
            fi
            ;;
        *)
            echo "Usage: $0 {start|monitor|stop|status}"
            echo "  start   - Start port-forward once"
            echo "  monitor - Start with automatic health monitoring and restart"
            echo "  stop    - Stop port-forward"
            echo "  status  - Check status"
            exit 1
            ;;
    esac
}

main "$@"
