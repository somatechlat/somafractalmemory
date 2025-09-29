#!/bin/bash
# Auto-restart and connect to SomaFractalMemory Kubernetes server
# This script makes everything automatic!

set -e

echo "🚀 Starting SomaFractalMemory Auto-Server..."

# Kill any existing port forwards
pkill -f "kubectl port-forward" 2>/dev/null || true

# Default ports (can be overridden via arguments)
DEFAULT_PORT=9595
DEV_PORT=${1:-$DEFAULT_PORT}
TEST_PORT=${2:-$DEFAULT_PORT}

# Wait for pods to be ready
echo "⏳ Waiting for server to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=api,app.kubernetes.io/instance=soma-memory --timeout=60s

# Get the current API pod name
API_POD=$(kubectl get pods -l app.kubernetes.io/component=api,app.kubernetes.io/instance=soma-memory -o jsonpath='{.items[0].metadata.name}')

echo "📡 Found API pod: $API_POD"

# Function to start a port-forward in background
start_forward() {
    local local_port=$1
    echo "🔗 Setting up port forwarding on port $local_port..."
    kubectl port-forward "$API_POD" "$local_port":9595 &
    echo $! > "port-forward-$local_port.pid"
}

# Start dev and test forwards (avoid duplicate if same)
if [[ $DEV_PORT -ne $TEST_PORT ]]; then
    start_forward $DEV_PORT
    start_forward $TEST_PORT
else
    start_forward $DEV_PORT
fi

# Wait a moment for forwarding to establish
sleep 3

# Test the connection for each port
for p in $DEV_PORT $TEST_PORT; do
    echo "🧪 Testing server on port $p..."
    if curl -s "http://localhost:${p}/healthz" >/dev/null; then
        echo "✅ Server on port $p is ready and responding!"
    else
        echo "❌ Server on port $p not responding. Check pod logs."
    fi
done

# Keep the script running to maintain port forwards
trap "
    echo 'Stopping server...';
    pkill -f 'kubectl port-forward';
    rm -f port-forward-*.pid;
    exit" INT TERM

# Wait indefinitely (press Ctrl+C to stop)
while true; do sleep 60; done
