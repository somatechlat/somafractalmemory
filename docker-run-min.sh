#!/usr/bin/env bash
# Local helper to build and run the minimal test image on port 9596
set -euo pipefail

IMAGE_TAG=somafractalmemory:minimal
CONTAINER_NAME=somafractalmemory_min_test

# Build
docker build -f Dockerfile.min -t ${IMAGE_TAG} .

# Run (map host 9596->container 9595). Use host.docker.internal for Redis/Qdrant on macOS
docker run -d --rm \
  --name ${CONTAINER_NAME} \
  -p 9596:9595 \
  -e SOMA_MODE=ON_DEMAND \
  -e SOMA_REDIS__HOST=host.docker.internal \
  -e SOMA_REDIS__PORT=6379 \
  -e SOMA_QDRANT__URL=http://host.docker.internal:6333 \
  ${IMAGE_TAG}

# Wait for health
echo "Waiting for /health on http://127.0.0.1:9596/health"
for i in {1..30}; do
  if curl -sS http://127.0.0.1:9596/health | grep -q 'kv_store'; then
    echo "healthy"
    exit 0
  fi
  sleep 1
done

echo "Container did not become healthy within timeout"
exit 2
