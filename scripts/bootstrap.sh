#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# Bootstrap script for SomaFractalMemory API container.
# Mode: STANDALONE — 100% Django patterns, gunicorn WSGI.
# No AAAS, no SomaBrain integration.
# ---------------------------------------------------------------------------

set -euo pipefail

echo "=== SomaFractalMemory Standalone Bootstrap ==="

# ---------------------------------------------------------------------------
# Standalone Django settings
# ---------------------------------------------------------------------------
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-somafractalmemory.settings.standalone}"
export PYTHONPATH="/app:${PYTHONPATH:-}"

echo "Settings: ${DJANGO_SETTINGS_MODULE}"
echo "DB Host: ${SOMA_DB_HOST:-localhost}"
echo "Redis Host: ${SOMA_REDIS_HOST:-not configured}"
echo "Milvus Host: ${SOMA_MILVUS_HOST:-not configured}"

# ---------------------------------------------------------------------------
# Wait for PostgreSQL to be ready (max 30s)
# ---------------------------------------------------------------------------
echo "Waiting for PostgreSQL..."
DB_HOST="${SOMA_DB_HOST:-localhost}"
DB_PORT="${SOMA_DB_PORT:-5432}"

for i in $(seq 1 30); do
    if python -c "
import socket
s = socket.create_connection(('${DB_HOST}', ${DB_PORT}), timeout=2)
s.close()
print('PostgreSQL is reachable')
" 2>/dev/null; then
        break
    fi
    echo "  Attempt ${i}/30 — PostgreSQL not ready yet..."
    sleep 1
done

# ---------------------------------------------------------------------------
# Run Django migrations
# ---------------------------------------------------------------------------
echo "Running Django migrations..."
python /app/manage.py migrate --noinput 2>&1 || {
    echo "WARNING: Django migrate failed on first attempt, retrying..."
    sleep 2
    python /app/manage.py migrate --noinput 2>&1 || {
        echo "ERROR: Django migrations failed. Starting anyway (tables may already exist)."
    }
}
echo "Django migrations complete."

# ---------------------------------------------------------------------------
# Start gunicorn — production WSGI server
# ---------------------------------------------------------------------------
echo "Starting gunicorn on port ${SOMA_API_PORT:-10101}..."

exec gunicorn somafractalmemory.config.wsgi:application \
    --bind "0.0.0.0:${SOMA_API_PORT:-10101}" \
    --workers "${GUNICORN_WORKERS:-1}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --log-level info
