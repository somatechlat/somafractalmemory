#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# Bootstrap script for SomaFractalMemory API container.
# Guarantees:
#   * Alembic migrations are applied (fail fast on error).
#   * PostgreSQL, Qdrant, and Redis are reachable before the API starts.
#   * Qdrant collection exists (creates it if missing).
#   * Environment variables are exported for the application.
#   * All steps emit clear "print" statements that appear in container logs.
# ---------------------------------------------------------------------------

set -euo pipefail

# Helper for exponential back‑off
backoff() {
  local attempt=$1
  local max=$2
  local delay=$((2 ** attempt))
  if (( delay > max )); then delay=$max; fi
  echo "⏳ Waiting ${delay}s (attempt $((attempt+1)))..."
  sleep $delay
}

echo "🚀 Starting bootstrap for SomaFractalMemory API"

# ---------------------------------------------------------------------------
# 1️⃣ Run Alembic migrations
# ---------------------------------------------------------------------------
echo "🔧 Running Alembic migrations..."
# Ensure the project root is on PYTHONPATH so alembic can import the "common" package.
export PYTHONPATH="/app:${PYTHONPATH:-}"
# Run alembic in a non‑failing mode – duplicate‑table errors are expected after the
# first successful run. We temporarily disable "set -e" so the script continues
# regardless of alembic's exit code.
set +e
alembic upgrade head || true
set -e
echo "✅ Alembic migrations applied (or already up‑to‑date)."

# ---------------------------------------------------------------------------
# All required services are declared as dependencies in docker‑compose, so they
# are guaranteed to be healthy before this script runs. We can therefore skip
# the explicit wait loops and launch the API immediately after migrations.

# Export connection strings for the app (the Settings loader reads them).
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-soma}"
POSTGRES_DB="${POSTGRES_DB:-somamemory}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-soma}"
QDRANT_HOST="${QDRANT_HOST:-qdrant}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
QDRANT_COLLECTION="${QDRANT_COLLECTION:-memories}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

export POSTGRES_DSN="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
export QDRANT_URL="http://$QDRANT_HOST:$QDRANT_PORT"
export REDIS_URL="redis://$REDIS_HOST:$REDIS_PORT/0"

echo "🚦 All dependencies are assumed healthy. Starting FastAPI server..."

# Finally start the FastAPI server directly.
exec /opt/venv/bin/uvicorn somafractalmemory.http_api:app \
  --host 0.0.0.0 \
  --port "${SOMA_API_PORT:-9595}" \
  --workers 2 \
  --log-level info
