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
- Shell: `export SOMA_API_TOKEN=your-token && docker compose --profile core up -d`
- .env file at repo root (see `.env.example`), then `docker compose --profile core up -d`.

Common variables:
- SOMA_API_TOKEN: Bearer token for API access (string)
- SOMA_API_TOKEN_FILE: Path to a file containing the token (string)
- JWT_ENABLED (optional): Enable JWT auth mode (bool-like)
- JWT_SECRET (optional): HMAC secret if JWT (HS256) is used (string)
- JWT_PUBLIC_KEY (optional): RSA public key if JWT (RS256) is used (PEM)
- JWT_ISSUER/JWT_AUDIENCE (optional): Validate iss/aud claims
- POSTGRES_PASSWORD: Postgres password (string)
- SOMA_API_PORT: API port inside container (int; default 10101)

## Production guidance

- **Never** commit real secrets to the repository.
- **Mandatory in Production**: Use HashiCorp Vault.
  - Set `SOMA_VAULT_URL` and `SOMA_VAULT_ROLE`.
  - Secrets are injected into process memory at startup.
- Rotate tokens regularly and audit usage.

## Rotation and audit

- Maintain an inventory of issued tokens and rotation dates.
- Log auth failures and suspicious access patterns.
- Prefer per-service or per-user tokens over shared tokens.

## Local quick check

- Start services: `docker compose --profile core up -d`
- Health: GET `http://127.0.0.1:10101/healthz`
- Use Authorization: `Bearer devtoken` for local tests unless overridden.
