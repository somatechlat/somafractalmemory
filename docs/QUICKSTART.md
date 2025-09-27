# Quickstart Guide

Follow these steps to get SomaFractalMemory running locally in minutes. All commands are derived from the current repository layout.

---

## 1. Clone & Install
```bash
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory
python -m venv .venv
source .venv/bin/activate
pip install -e .
```
This installs the `somafractalmemory` package and the `soma` CLI entry point.

---

## 2. Start Supporting Services (Docker Compose)
```bash
cp .env.example .env
docker compose up -d
```
The compose file launches Redis, Postgres, Qdrant, Redpanda, the API (`http://localhost:9595`), the background consumer, and a sandbox API (`http://localhost:8888`).

Stop the stack with `docker compose down` (add `-v` to wipe volumes).

---

## 3. Store & Recall From Python
```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

mem = create_memory_system(
    MemoryMode.DEVELOPMENT,
    "quickstart",
    config={
        "redis": {"testing": True},
        "qdrant": {"path": "./qdrant.db"},
    },
)

mem.store_memory((0.0, 0.0, 0.0), {"task": "quickstart", "importance": 4}, MemoryType.EPISODIC)
print(mem.recall("quickstart"))
```
Run the snippet from a Python shell with your virtual environment activated.

---

## 4. Try the CLI
```bash
soma --mode development --namespace quickstart store \
  --coord "1,2,3" \
  --payload '{"note": "CLI demo", "importance": 2}'

soma --mode development --namespace quickstart recall --query "CLI"
```
Use `--config-json` if you need to specify Redis/Postgres/Qdrant endpoints explicitly.

---

## 5. Hit the API
With Docker Compose running, send requests to the FastAPI example:
```bash
curl -X POST http://localhost:9595/store \
  -H 'Content-Type: application/json' \
  -d '{"coord": "2,4,6", "payload": {"note": "API"}}

curl -X POST http://localhost:9595/recall \
  -H 'Content-Type: application/json' \
  -d '{"query": "API"}'
```
Enable bearer auth by setting `SOMA_API_TOKEN` in `.env`; include `Authorization: Bearer <token>` headers when enabled.

Docs and metrics:
- Swagger UI: <http://localhost:9595/docs>
- Prometheus metrics: <http://localhost:9595/metrics>

---

## 6. Explore Events & Consumers
1. Ensure `EVENTING_ENABLED=true` in `.env`.
2. Produce a memory (CLI or API).
3. Observe consumer logs:
   ```bash
   docker compose logs -f consumer
   ```
4. Check consumer metrics at <http://localhost:8001/metrics>.

---

## 7. Shut Down & Cleanup
```bash
docker compose down          # stop services, keep data
rm -rf qdrant.db             # remove local Qdrant file created by quickstart
```
Re-run the quickstart anytime—fake Redis and local Qdrant make it easy to iterate.

---

*Need more detail? Dive into `docs/CONFIGURATION.md` for tunables and `docs/api.md` for the full method reference.*
