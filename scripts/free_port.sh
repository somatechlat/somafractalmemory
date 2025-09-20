#!/usr/bin/env bash
# Free a TCP port by politely terminating any processes listening on it.
# Usage: ./scripts/free_port.sh 9595

PORT=${1:-9595}
if [ -z "$PORT" ]; then
  echo "No port specified"
  exit 1
fi
PIDS=$(lsof -tiTCP:${PORT} -sTCP:LISTEN || true)
if [ -z "$PIDS" ]; then
  echo "Port ${PORT} is free"
  exit 0
fi
echo "Found PIDs listening on port ${PORT}: $PIDS"
# Try graceful shutdown
kill $PIDS 2>/dev/null || true
sleep 1
PIDS2=$(lsof -tiTCP:${PORT} -sTCP:LISTEN || true)
if [ -z "$PIDS2" ]; then
  echo "Port ${PORT} freed after SIGTERM"
  exit 0
fi
# Force kill
echo "Still present after SIGTERM: $PIDS2. Sending SIGKILL..."
kill -9 $PIDS2 2>/dev/null || true
sleep 0.5
PIDS3=$(lsof -tiTCP:${PORT} -sTCP:LISTEN || true)
if [ -z "$PIDS3" ]; then
  echo "Port ${PORT} freed after SIGKILL"
  exit 0
fi
echo "Failed to free port ${PORT}; processes still present: $PIDS3"
exit 2
