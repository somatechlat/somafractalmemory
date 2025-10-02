#!/bin/bash
# Start dual API servers: DEV on port 9595, TEST on port 9999
# Uses service discovery - no hardcoded ports!

set -e

echo "🚀 Starting Dual SomaFractalMemory Servers..."
echo "   📋 DEV server → localhost:9595"
echo "   🧪 TEST server → localhost:9999"

# Kill any existing port forwards
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 2

# Function to wait for pod readiness
wait_for_pods() {
    local namespace=$1
    local instance=$2
    echo "⏳ Waiting for pods in namespace '$namespace'..."

    # Wait for infrastructure pods
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=$instance --namespace=$namespace --timeout=180s || true

    # Check what's actually ready
    kubectl get pods -n $namespace -l app.kubernetes.io/instance=$instance
}

# Function to start port forward if pod exists
setup_port_forward() {
    local namespace=$1
    local instance=$2
    local port=$3
    local label=$4

    echo "🔗 Setting up $label port forwarding on port $port..."

    # Try to find any running pod for the API
    API_POD=$(kubectl get pods -n $namespace -l app.kubernetes.io/instance=$instance -l app.kubernetes.io/component=api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [[ -n $API_POD ]] && [[ $API_POD != "" ]]; then
        echo "📡 Found API pod: $API_POD in namespace $namespace"
        kubectl port-forward -n $namespace "$API_POD" "$port":9595 &
        echo $! > "port-forward-$port.pid"

        # Test the connection after a moment
        sleep 3
        if curl -s --max-time 5 "http://localhost:${port}/healthz" >/dev/null 2>&1; then
            echo "✅ $label server on port $port is ready and responding!"
        else
            echo "⚠️  $label server on port $port forwarded but not yet responding (may still be starting up)"
        fi
    else
        echo "❌ No API pod found for $label in namespace $namespace"
    fi
}

# Wait for and setup DEV server (default namespace)
wait_for_pods "default" "soma-memory"
setup_port_forward "default" "soma-memory" "9595" "DEV"

# Wait for and setup TEST server (soma-test namespace)
wait_for_pods "soma-test" "soma-memory-test"
setup_port_forward "soma-test" "soma-memory-test" "9999" "TEST"

echo ""
echo "🎉 Dual server setup complete!"
echo "   📋 DEV API:  http://localhost:9595/healthz"
echo "   🧪 TEST API: http://localhost:9999/healthz"
echo ""
echo "Press Ctrl+C to stop all port forwards..."

# Keep the script running to maintain port forwards
trap "
    echo 'Stopping all servers...';
    pkill -f 'kubectl port-forward';
    rm -f port-forward-*.pid;
    exit" INT TERM

# Wait indefinitely
while true; do sleep 60; done
