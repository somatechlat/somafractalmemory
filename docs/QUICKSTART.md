# Quickstart — Run the example API locally

This quickstart shows how to get the example FastAPI service running locally with a lightweight dev environment.

Requirements
- Python 3.10+
- Docker (optional)

1) Create a virtualenv and install the package in editable mode

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-min.txt  # optional: minimal deps for examples
```

2) Run the example API (FastAPI) locally

```bash
# from the repo root
uvicorn examples.api:app --reload --port 9595
```

3) Try a sample curl

```bash
curl -X GET http://127.0.0.1:9595/health
```

4) Developer compose (optional)

Create a local `docker-compose.dev.yml` with Redis and a Qdrant-lite container if you want a full stack integration. Use the `docker-run-min.sh` helper to build and run the minimal image.

Notes
- For development you can set `SOMA_REDIS__TESTING=true` (or pass a `config` dict to `create_memory_system`) to use an in-memory FakeRedis for tests.
- If `requirements-min.txt` is not present, run `python scripts/generate_requirements.py requirements-min.yaml requirements-min.txt` to generate it from the YAML manifest.

See `docs/README.md` for more documentation on building and publishing docs.
