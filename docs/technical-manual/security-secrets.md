---
title: "Security and Secrets (Dev vs Prod)"
project: "somafractalmemory"
last_modified: "2025-10-25"
---

# Security and Secrets (Dev vs Prod)

This document explains how secrets are handled for local development versus production.

## Development defaults

- The Docker Compose file pins the API token to a predictable value for local testing:
  - SOMA_API_TOKEN = "devtoken"
- This makes the e2e examples work out of the box.
- Do not reuse this token in any non-dev environment.

## Overriding secrets

You can override the default token and other settings without editing compose by using an `.env` file or shell env vars.

Options (precedence: shell > .env > compose defaults):
- Shell: export SOMA_API_TOKEN=your-token && docker compose --profile core up -d
- .env file at repo root (see `.env.example`), then `docker compose --profile core up -d`.

Common variables:
- SOMA_API_TOKEN: Bearer token for API access (string)
- POSTGRES_PASSWORD: Postgres password (string)
- SOMA_API_PORT: API port inside container (int; default 9595)
- JWT_SECRET (optional): HMAC secret if JWT auth is used (string)

## Production guidance

- Never commit real secrets to the repository.
- Use a secrets manager (e.g., AWS Secrets Manager, GCP Secret Manager, Vault) and inject at runtime (env or files).
- Rotate tokens regularly and audit usage.
- Restrict `SOMA_API_TOKEN` scope by environment and role; prefer short TTL tokens or JWT with exp/iat claims.

## Rotation and audit

- Maintain an inventory of issued tokens and rotation dates.
- Log auth failures and suspicious access patterns.
- Prefer per-service or per-user tokens over shared tokens.

## Local quick check

- Start services: `docker compose --profile core up -d`
- Health: GET `http://127.0.0.1:9595/healthz`
- Use Authorization: `Bearer devtoken` for local tests unless overridden.
