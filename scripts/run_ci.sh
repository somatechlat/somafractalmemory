#!/bin/bash
# Perfect CI runner for SomaFractalMemory
# This script ensures all services are available before running tests

set -e

echo "🚀 Starting Perfect SomaFractalMemory CI Run..."

# Kill any existing port forwards
pkill -f "kubectl port-forward" 2>/dev/null || true
echo "✅ Cleaned up existing port forwards"

# Check if Kubernetes deployment exists
if ! kubectl get pods -l app.kubernetes.io/instance=soma-memory -n soma-memory >/dev/null 2>&1; then
    echo "❌ No Kubernetes deployment found in namespace soma-memory. Please run: helm upgrade soma-memory ./helm"
    exit 1
fi

# Wait for essential pods to be ready (API is required, others are optional)
echo "⏳ Waiting for API pod to be ready..."
if ! kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=api,app.kubernetes.io/instance=soma-memory -n soma-memory --timeout=120s; then
    echo "❌ API pod not ready - cannot proceed"
    exit 1
fi

# Re‑fetch the current API pod name (it may have changed during the wait)
API_POD=$(kubectl get pod -l app.kubernetes.io/component=api,app.kubernetes.io/instance=soma-memory -n soma-memory -o jsonpath='{.items[0].metadata.name}')

# Get other infra pod names (optional)
POSTGRES_POD=$(kubectl get pod -l app.kubernetes.io/component=postgres,app.kubernetes.io/instance=soma-memory -n soma-memory -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
REDIS_POD=$(kubectl get pod -l app.kubernetes.io/component=redis,app.kubernetes.io/instance=soma-memory -n soma-memory -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
QDRANT_POD=$(kubectl get pod -l app.kubernetes.io/component=qdrant,app.kubernetes.io/instance=soma-memory -n soma-memory -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
REDPANDA_POD=$(kubectl get pod -l app.kubernetes.io/component=redpanda,app.kubernetes.io/instance=soma-memory -n soma-memory -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

echo "📡 Found API pod: $API_POD"
if [[ -n $REDPANDA_POD ]]; then
    # Check if Redpanda pod is actually running
    POD_STATUS=$(kubectl get pod "$REDPANDA_POD" -n soma-memory -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
    if [[ "$POD_STATUS" == "Running" ]]; then
        echo "📡 Found Redpanda pod: $REDPANDA_POD"
    else
        echo "⚠️ Redpanda pod exists but not running (status: $POD_STATUS) - Kafka tests will be skipped"
        REDPANDA_POD=""
    fi
else
    echo "⚠️ No Redpanda pod found - Kafka tests will be skipped"
fi

# Start port forwards in background for API and required services
echo "🔗 Setting up port forwarding..."
# API ports
kubectl port-forward -n soma-memory "$API_POD" 9595:9595 &
API_PF_PID=$!
# Optional test port (keep for compatibility)
kubectl port-forward -n soma-memory "$API_POD" 9999:9595 &
TEST_PF_PID=$!

# Forward infra services if pods are found
if [[ -n $POSTGRES_POD ]]; then
    kubectl port-forward -n soma-memory "$POSTGRES_POD" 5433:5432 &
    POSTGRES_PF_PID=$!
    echo "✅ Postgres forward (PID: $POSTGRES_PF_PID)"
fi
if [[ -n $REDIS_POD ]]; then
    kubectl port-forward -n soma-memory "$REDIS_POD" 6380:6379 &
    REDIS_PF_PID=$!
    echo "✅ Redis forward (PID: $REDIS_PF_PID)"
fi
if [[ -n $QDRANT_POD ]]; then
    kubectl port-forward -n soma-memory "$QDRANT_POD" 6333:6333 &
    QDRANT_PF_PID=$!
    echo "✅ Qdrant forward (PID: $QDRANT_PF_PID)"
fi

# Kafka (Redpanda) – optional
if [[ -n $REDPANDA_POD ]]; then
    kubectl port-forward -n soma-memory "$REDPANDA_POD" 9092:9092 &
    KAFKA_PF_PID=$!
    echo "✅ Kafka forward (PID: $KAFKA_PF_PID)"
else
    echo "⚠️ No Redpanda pod found – Kafka tests will be skipped"
    KAFKA_PF_PID=""
fi

# Wait a bit for forwards to settle
sleep 5

# Test connectivity
echo "🧪 Testing service connectivity..."
for port in 9595 9999; do
    if curl -s "http://localhost:${port}/healthz" >/dev/null; then
        echo "✅ API on port $port is responding"
    else
        echo "❌ API on port $port is not responding"
        exit 1
    fi
done

# Test Kafka connectivity if available
if [[ -n $KAFKA_PF_PID ]] && kill -0 $KAFKA_PF_PID 2>/dev/null; then
    echo "✅ Kafka port forward is active"
else
    echo "⚠️ Kafka port forward not active - some tests may be skipped"
fi

# Clean up function
cleanup() {
    echo "🧹 Cleaning up..."
    [[ -n $API_PF_PID ]] && kill $API_PF_PID 2>/dev/null || true
    [[ -n $TEST_PF_PID ]] && kill $TEST_PF_PID 2>/dev/null || true
    [[ -n $KAFKA_PF_PID ]] && kill $KAFKA_PF_PID 2>/dev/null || true
    pkill -f "kubectl port-forward" 2>/dev/null || true
}

# Set up cleanup on exit
trap cleanup EXIT INT TERM

# Export environment variables for tests
export USE_REAL_INFRA=1
export REDIS_URL="redis://localhost:6380/0"
export POSTGRES_URL="postgresql://postgres:postgres@localhost:5433/somamemory"
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"

# Run the test suite
echo "🧪 Running test suite..."
if ./.venv/bin/pytest -q; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed"
    exit 1
fi
