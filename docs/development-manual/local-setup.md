---
title: "Local Development Setup"
purpose: "Step-by-step instructions for running SomaFractalMemory directly on a developer workstation."
audience:
  - "Developers and Contributors"
last_updated: "2025-10-17"
---

# Local Development Setup

1. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   pip install -r api-requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   export SOMA_API_TOKEN=dev-token
   export SOMA_POSTGRES_URL=postgresql://soma:soma@localhost:40021/somamemory
   export QDRANT_URL=http://localhost:40023
   ```

4. **Run the API**
   ```bash
   uvicorn somafractalmemory.http_api:app --reload --host 0.0.0.0 --port 9595
   ```

5. **Smoke test**
   ```bash
   curl -H "Authorization: Bearer ${SOMA_API_TOKEN}" http://localhost:9595/stats
   curl -H "Authorization: Bearer ${SOMA_API_TOKEN}" -H "Content-Type: application/json" \
     -d '{"coord":"0,0","payload":{"message":"hello"}}' \
     http://localhost:9595/memories
   ```

6. **CLI**
   ```bash
   python -m somafractalmemory.cli store --coord 0,0 --payload '{"message":"cli"}'
   python -m somafractalmemory.cli search --query cli
   ```

> The development workflow does not expose any deprecated `store`/`recall` routes. All tooling should operate through `/memories`.
