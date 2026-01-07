---
title: "Developer Environment (VS Code)"
last_modified: "2025-10-29"
---

# 🧑‍💻 Developer Environment (VS Code)

This guide gets you from clone → running API → tests passing using macOS + zsh + VS Code.

## ✅ Prerequisites

- macOS with zsh (default)
- Docker Desktop (Compose v2 enabled)
- Python 3.10+
- VS Code
- Recommended VS Code extensions:
  - Python, Pylance, Ruff, Docker, YAML, Markdown All in One, GitLens

## 📦 Clone and Python environment

```bash
git clone https://github.com/somatechlat/somafractalmemory
cd somafractalmemory

# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install runtime + API + dev tooling
pip install -U pip
pip install -e ".[api,dev]"
```

In VS Code: select the interpreter at .venv/bin/python (Cmd+Shift+P → Python: Select Interpreter).

## 🔐 Environment configuration (.env)

```bash
cp .env.example .env
```

Edit .env:
- SOMA_API_TOKEN=devtoken (for local only; use a strong token otherwise)
- Optional for browser apps: SOMA_CORS_ORIGINS=https://your-app.example
- Optional rate limiting (disable for heavy seeding):
  - SOMA_RATE_LIMIT_MAX=0
  - SOMA_RATE_LIMIT_WINDOW_SECONDS=0

## 🚀 Run the full stack (Docker Compose)

```bash
docker compose --profile core up -d
```

What this starts: Postgres, Redis, Qdrant, and the API on http://127.0.0.1:10101.

Health check:

```bash
curl -fsS http://127.0.0.1:10101/healthz
```

Write a test memory:

```bash
curl -s -X POST http://127.0.0.1:10101/memories \
  -H 'Authorization: Bearer devtoken' \
  -H 'Content-Type: application/json' \
  -d '{"coord":"0.1,0.2,0.3","payload":{"ok":true},"memory_type":"episodic"}'
```

## 🧪 Tests, type checks, lint

```bash
pytest -q -ra
mypy somafractalmemory
ruff check .
```

## � View the docs locally

Build the static docs site (outputs to `site/`):

```bash
python -m mkdocs build
```

Preview with live reload:

```bash
python -m mkdocs serve -a 127.0.0.1:8000
```

Now open http://127.0.0.1:8000. Stop the server with Ctrl+C. If the port stays busy, free it:

```bash
kill $(lsof -ti:8000) 2>/dev/null || true
```

Note: You may see a deprecation warning about `cards_color` in the social plugin. It’s harmless and doesn’t affect the docs.

## �🐞 Debugging the API in VS Code

Launch target (add to .vscode/launch.json if you keep one):

```json
{
  "name": "Run API (uvicorn)",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": [
    "somafractalmemory.http_api:app",
    "--host", "0.0.0.0",
    "--port", "10101"
  ],
  "envFile": "${workspaceFolder}/.env",
  "jinja": true,
  "justMyCode": true
}
```

Tip: The API expects SOMA_API_TOKEN (or SOMA_API_TOKEN_FILE). /health and /healthz don’t require auth.

## ❗ Common pitfalls (and quick fixes)

- “no service selected”: include the profile → `docker compose --profile core up -d`
- 429 Too Many Requests during seeding: set SOMA_RATE_LIMIT_MAX=0 and SOMA_RATE_LIMIT_WINDOW_SECONDS=0
- Corrupted dev volumes (Redis/Postgres):
  - `docker compose --profile core down`
  - `docker volume rm somafractalmemory_pgdata somafractalmemory_redisdata`
  - `docker compose --profile core up -d`
- Port 10101 busy: change API_PORT in .env and re-up the stack

## 🔎 Where things are

- API app: `somafractalmemory/http_api.py`
- Compose: `docker-compose.yml`
- Docs home: `docs/README.md`
- Token guidance: `docs/technical-manual/security-secrets.md`

That’s it — you should be able to run, debug, and test locally in minutes.
