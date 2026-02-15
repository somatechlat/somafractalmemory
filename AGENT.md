# SomaFractalMemory (SFM) - Agent Context

Purpose: a single, code-accurate reference for working in this repo.

## What This Repo Is

SomaFractalMemory is an HTTP memory service (Django + Django Ninja) providing:
- Memory CRUD: store/retrieve/delete by fractal coordinate string
- Search: semantic search via Milvus when configured (fallback to ORM text search)
- Graph operations: link, neighbors, shortest path (ORM-backed)

## Canonical Entry Points

- Django settings: `somafractalmemory/settings/__init__.py`
- Standalone settings profile (used by the standalone compose): `somafractalmemory/settings/standalone.py`
- API wiring (Ninja routers): `somafractalmemory/api/core.py`
- Django URL mount (API at root): `somafractalmemory/config/urls.py`
- Service layer (business logic): `somafractalmemory/admin/core/services.py`
- Compatibility service exports: `somafractalmemory/services.py`

## Local Standalone Run (Docker Compose)

```bash
cd somafractalmemory
cp .env.example .env
docker compose -f infra/standalone/docker-compose.yml up -d
curl -fsS http://127.0.0.1:10101/healthz
```

Host ports (standalone compose):
- API: `10101`
- Postgres: `10432`
- Redis: `10379`
- Milvus: `10530`

## Required Environment Variables (Standalone Compose)

These are required by `infra/standalone/docker-compose.yml`:
- `SOMA_API_TOKEN`
- `SFM_DB_PASSWORD`
- `SFM_VAULT_TOKEN`
- `SFM_MINIO_ROOT_USER`
- `SFM_MINIO_ROOT_PASSWORD`

## HTTP Surface (Code Truth)

Base URL: `http://127.0.0.1:10101`

- `GET /healthz`
- `GET /readyz`
- `GET /health`
- `GET /stats`
- `POST /memories` (body: `{"coord": "...", "payload": {...}, "memory_type": "episodic|semantic"}`)
- `GET /memories/{coord}`
- `DELETE /memories/{coord}`
- `POST /memories/search`
- `POST /graph/link`
- `GET /graph/neighbors`
- `GET /graph/path`

Most non-health routes require `Authorization: Bearer <token>` (see `somafractalmemory/admin/aaas/auth.py`).
