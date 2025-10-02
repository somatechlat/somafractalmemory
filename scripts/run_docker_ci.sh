#!/bin/bash
# Simple Docker-based CI for SomaFractalMemory
# Uses only Docker services for maximum reliability

set -e

echo "🚀 Starting SomaFractalMemory Docker CI..."

# Ensure Docker services are running
echo "🐳 Starting Docker services..."
docker compose up -d redis postgres qdrant redpanda

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

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
