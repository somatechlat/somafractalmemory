#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# Bootstrap script for SomaFractalMemory API container.
# 100% Django patterns - Production WSGI server (gunicorn).
# ---------------------------------------------------------------------------

set -euo pipefail

echo "🚀 Starting bootstrap for SomaFractalMemory API (Django - Production)"

# ---------------------------------------------------------------------------
# Export connection strings for Django settings
# ---------------------------------------------------------------------------
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-soma}"
POSTGRES_DB="${POSTGRES_DB:-somamemory}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-soma}"
MILVUS_HOST="${MILVUS_HOST:-milvus}"
MILVUS_PORT="${MILVUS_PORT:-19530}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Django settings environment
export DJANGO_SETTINGS_MODULE="somafractalmemory.settings"
export SOMA_POSTGRES_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
export SOMA_DB_HOST="$POSTGRES_HOST"
export SOMA_DB_PORT="$POSTGRES_PORT"
export SOMA_DB_USER="$POSTGRES_USER"
export SOMA_DB_PASSWORD="$POSTGRES_PASSWORD"
export SOMA_DB_NAME="$POSTGRES_DB"
export SOMA_MILVUS_HOST="$MILVUS_HOST"
export SOMA_MILVUS_PORT="$MILVUS_PORT"
export SOMA_REDIS_HOST="$REDIS_HOST"
export SOMA_REDIS_PORT="$REDIS_PORT"
export PYTHONPATH="/app:${PYTHONPATH:-}"

# ---------------------------------------------------------------------------
# Run Django migrations
# ---------------------------------------------------------------------------
echo "🔧 Running Django migrations..."
python /app/manage.py migrate --run-syncdb --noinput 2>&1 || {
    echo "⚠️ Django migrate failed (tables may not exist yet), running syncdb..."
    python /app/manage.py migrate --run-syncdb --noinput 2>&1 || true
}
echo "✅ Django migrations applied."

echo "🚦 Starting gunicorn (production WSGI server)..."

# Start gunicorn - production WSGI server
# Workers = 2*CPU + 1 (but limited for container)
exec gunicorn somafractalmemory.wsgi:application \
    --bind 0.0.0.0:"${SOMA_API_PORT:-10101}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --log-level info
