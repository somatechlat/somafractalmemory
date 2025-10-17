---
title: "Backup & Recovery"
purpose: "This playbook explains how to protect the data behind the `/memories` API."
audience:
  - "Operators and SREs"
last_updated: "2025-10-16"
---

# Backup & Recovery

This playbook explains how to protect the data behind the `/memories` API.

## PostgreSQL

- **Backups**: Use daily logical dumps via `pg_dump` or enable WAL archiving.
  ```bash
  pg_dump --dbname=$SOMA_POSTGRES_URL --file=/backups/sfm-$(date +%F).sql
  ```
- **Retention**: Keep 30 days of dumps encrypted at rest. Rotate keys quarterly.
- **Restore**:
  ```bash
  psql $SOMA_POSTGRES_URL < /backups/sfm-2025-10-16.sql
  ```
  After restoring, restart the API to rebuild vector caches.

## Qdrant

- Enable the snapshot feature via `qdrant snapshot create <collection>`. Store snapshots alongside Postgres dumps.
- When restoring, replay snapshots before restarting the API. The `/memories` endpoints remain read-only until Qdrant is back online.

## Redis (Optional)

Redis is only used for rate limiting. If it fails, the API falls back to an in-memory limiter. Backups are not required.

## Disaster Recovery Checklist

1. Declare an incident and freeze writes to `/memories` by revoking the API token.
2. Restore PostgreSQL from the most recent good dump.
3. Restore Qdrant snapshot.
4. Rotate `SOMA_API_TOKEN` and redeploy the API.
5. Execute synthetic smoke tests (`store → search → get → delete`).
6. Re-enable external traffic and close the incident with a timeline.
