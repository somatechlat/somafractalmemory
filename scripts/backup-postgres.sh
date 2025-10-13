#!/usr/bin/env bash
# Simple postgres backup helper for docker-compose local Postgres service.
# Usage: scripts/backup-postgres.sh [container_name] [output_file]

set -euo pipefail
CONTAINER=${1:-somafractalmemory_postgres_1}
OUTFILE=${2:-./backups/postgres-$(date +%Y%m%d%H%M%S).sql}
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$REPO_ROOT/backups"

echo "Streaming pg_dump from container: $CONTAINER to $OUTFILE"
# Assumes container has pg_dump and env var PGUSER/PGPASSWORD/PGHOST/PGPORT are set or defaults apply
docker exec -i "$CONTAINER" pg_dump -U postgres --format=custom --file - > "$OUTFILE" || {
  echo "pg_dump failed. Check container name and credentials." >&2
  exit 1
}

echo "Backup written to $OUTFILE"
