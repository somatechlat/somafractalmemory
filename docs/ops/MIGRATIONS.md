# Database Migration Runbook

This runbook explains how to manage Postgres schema migrations for Soma Fractal Memory using Alembic. The project now ships with a canonical migration history in `alembic/` that creates the `kv_store` and `memory_events` tables consumed by the API and workers.

## Prerequisites

- Python environment with the project dependencies plus Alembic. Install via `uv sync --extra ops` or `pip install -e .[ops]`.
- Network access to the target Postgres instance. The connection string is taken from the `POSTGRES_URL` environment variable; otherwise the fallback in `alembic.ini` is used.

## Common tasks

### Upgrade to the latest schema

```bash
export POSTGRES_URL="postgresql://<user>:<password>@<host>:5432/somamemory?sslmode=require"
uv run alembic upgrade head
```

### Check current revision

```bash
uv run alembic current
```

### Generate a new migration skeleton

```bash
uv run alembic revision -m "describe change"
```

Edit the generated file under `alembic/versions/` and fill in the required DDL using Alembic operations. All migrations should be idempotent and rely on Postgres-native types (JSONB, UUID, etc.).

## Operational guidance

- Run migrations as part of your deployment pipeline before rolling the application pods.
- Capture the Alembic output and include it in the production evidence log for the corresponding change ticket.
- Back up the database (or ensure point-in-time recovery is enabled) prior to applying structural changes.
- Keep the migration history linear for now. If branching becomes necessary, document the merge strategy explicitly in this runbook.

For deeper customization (e.g., offline migrations or multi-database environments), edit `alembic/env.py`. The environment script already respects `POSTGRES_URL`, so separate environments can inject their own credentials via secrets.
