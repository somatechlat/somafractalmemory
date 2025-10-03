#!/usr/bin/env bash
set -euo pipefail

NAMESPACE=${SOMA_NAMESPACE:-somabrain}
IMAGE_REPO=${SOMA_IMAGE_REPO:-somafractalmemory-runtime}
IMAGE_TAG=${SOMA_IMAGE_TAG:-dev}
VALUES_BASE=helm/values.yaml
VALUES_PERSIST=helm/values-dev-full-persistent.yaml
RELEASE=${SOMA_HELM_RELEASE:-somabrain}
PORT=${SOMA_PORT:-9696}

echo "[somabrain] Deploying release=$RELEASE ns=$NAMESPACE image=${IMAGE_REPO}:${IMAGE_TAG} port=$PORT"

helm upgrade --install "$RELEASE" ./helm \
  -n "$NAMESPACE" --create-namespace \
  -f "$VALUES_BASE" \
  -f "$VALUES_PERSIST" \
  --set image.repository="$IMAGE_REPO" \
  --set image.tag="$IMAGE_TAG" \
  --wait --timeout=600s

echo "[somabrain] Port-forwarding service to localhost:$PORT (Ctrl+C to stop)" >&2
kubectl -n "$NAMESPACE" port-forward svc/${RELEASE}-somafractalmemory $PORT:$PORT
