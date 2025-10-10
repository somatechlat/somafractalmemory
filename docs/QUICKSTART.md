# Quickstart Guide

Follow these steps to get SomaFractalMemory running locally in minutes. All commands are derived from the current repository layout.

---

## 1. Clone & Install (uv recommended)
```bash
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory
curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
uv sync --extra api --extra events --extra dev
```
This installs the `somafractalmemory` package (editable), the `soma` CLI, and developer tooling into `.venv`. Prefer `uv run …` to execute commands without manual activation. If you cannot use `uv`:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[api,events,dev]
```

---

## 2. Start Supporting Services (Docker Compose)
```bash
docker compose up -d
# optional: start the consumer profile when you need background reconciliation
docker compose --profile consumer up -d somafractalmemory_kube
```
The compose file launches Redis, Postgres, Qdrant, Kafka (Confluent single-broker), the FastAPI service on `http://localhost:9595`, and an auxiliary API on `http://localhost:8888`. Configuration lives directly in `docker-compose.yml`; no `.env` copy is required.

Health check and teardown:
```bash
curl -s http://localhost:9595/healthz | jq .
docker compose logs -f api  # stop with Ctrl+C when ready
docker compose down          # add -v to wipe volumes
```

---

## 3. Store & Recall From Python
```bash
uv run python - <<'PY'
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
PY
```
This snippet exercises the in-process development mode (fakeredis + file-based Qdrant) without needing Docker.

---

## 4. Try the CLI
```bash
uv run soma --mode development --namespace quickstart store \
  --coord "1,2,3" \
  --payload '{"note": "CLI demo", "importance": 2}'

uv run soma --mode development --namespace quickstart recall --query "CLI"
```
Use `--config-json` if you need to specify Redis/Postgres/Qdrant endpoints explicitly.

---

## 5. Hit the API
With Docker Compose running, send requests to the FastAPI example:
```bash
curl -X POST http://localhost:9595/store \
  -H 'Content-Type: application/json' \
  -d '{"coord": "2,4,6", "payload": {"note": "API"}}'

curl -X POST http://localhost:9595/recall \
  -H 'Content-Type: application/json' \
  -d '{"query": "API"}'
```
Enable bearer auth by setting `SOMA_API_TOKEN` in the API service environment (edit `docker-compose.yml` or an override file); include `Authorization: Bearer <token>` headers when enabled.

Docs and metrics:
- Swagger UI: <http://localhost:9595/docs>
- Prometheus metrics: <http://localhost:9595/metrics>

Kubernetes alternative (dev):
- Use the Helm chart with `helm/values-dev-port9797.yaml` to run the API on 9797 and expose it on your host via NodePort 30797. Then hit `http://127.0.0.1:30797/healthz`.

---

## 6. Explore Events & Consumers
1. Ensure `docker compose --profile consumer up -d somafractalmemory_kube` is running (consumer depends on Kafka and will retry until ready).
2. Produce a memory (CLI or API).
3. Observe consumer logs:
  ```bash
  docker compose --profile consumer logs -f somafractalmemory_kube
  ```
4. Inspect Kafka topics if needed:
  ```bash
  docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
  ```

---

## 7. Shut Down & Cleanup
```bash
docker compose down          # stop services, keep data
rm -rf qdrant.db             # remove local Qdrant file created by quickstart
```
Re-run the quickstart anytime—fake Redis and local Qdrant make it easy to iterate.

Persistence notes:
- Docker Compose data persists across restarts via named volumes; wipe with `docker compose down -v`.
- The dev Helm chart disables persistence by default; enable PVCs in values or apply `k8s/pvcs.yaml` for Kind when you want durable local data.

---

*Need more detail? Dive into `docs/CONFIGURATION.md` for tunables and `docs/api.md` for the full method reference.*

> WARNING
>
> For team compliance, prefer running against the real Docker Compose or Kind stack for integration and contract tests. Avoid mocks and altered production values in tests. Use dedicated test environments and realistic fixtures.
