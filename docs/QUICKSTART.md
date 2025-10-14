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
The recommended way to start the complete stack is to use the automatic port assignment script. This will prevent conflicts with any other services running on your machine.

### One-Command Evented Enterprise Stack:
```bash
./scripts/assign_ports_and_start.sh
# OR
make setup-dev
```

This script will:
- ✅ **Automatically detect and resolve port conflicts**
- ✅ Assign free ports to all infrastructure services
- ✅ Start complete evented enterprise stack (API + Consumer + PostgreSQL + Redis + Qdrant + Kafka)
- ✅ Display final port assignments
- ✅ Ensure **zero conflicts** with existing services

### Server Access:
- **Memory API**: http://localhost:9595 (fixed)
- **Health**: http://localhost:9595/healthz
- **Stats**: http://localhost:9595/stats
- **API Docs**: http://localhost:9595/docs
- **Infrastructure ports**: Auto-assigned (displayed at startup)

Health check and teardown:
```bash
make compose-health
make compose-logs  # stop with Ctrl+C when ready
make compose-down  # add '-v' equivalent: make compose-down-v
```

---

## 3. Store & Recall From Python
```bash
uv run python - <<'PY'
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

mem = create_memory_system(
  MemoryMode.EVENTED_ENTERPRISE,
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
This snippet exercises the single supported mode. Provide `redis.testing=True` or `vector.backend="memory"` in config to run without external services.

---

## 4. Try the CLI
```bash
uv run soma --mode evented_enterprise --namespace quickstart store \
  --coord "1,2,3" \
  --payload '{"note": "CLI demo", "importance": 2}'

uv run soma --mode evented_enterprise --namespace quickstart recall --query "CLI"
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
Set `SOMA_API_TOKEN` in the API service environment (edit `docker-compose.yml` or an override file); all client calls must include `Authorization: Bearer <token>`.

Docs and metrics:
- Swagger UI: <http://localhost:9595/docs>
- Prometheus metrics: <http://localhost:9595/metrics>

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
Need a clean slate across all compose files? Run `scripts/reset-sharedinfra-compose.sh` to stop compose stacks, prune named volumes (Redis/Postgres/Kafka/Qdrant), and remove legacy SomaStack volumes before starting fresh.
Re-run the quickstart anytime—fake Redis and local Qdrant make it easy to iterate.

Persistence notes:
- Docker Compose data persists across restarts via named volumes; wipe with `docker compose down -v`.
- The dev Helm chart disables persistence by default; enable PVCs in values or apply `k8s/pvcs.yaml` for Kind when you want durable local data.

---

*Need more detail? Dive into `docs/CONFIGURATION.md` for tunables and `docs/api.md` for the full method reference.*

Testing notes:
- For real-infra tests, export `USE_REAL_INFRA=1` and ensure the Compose stack is running (includes Kafka and the background consumer). Tests verify Qdrant indexing via payload filters and probe across common collections to avoid scroll-order flakiness.

> WARNING
>
> For team compliance, prefer running against the real Docker Compose or Kind stack for integration and contract tests. Avoid mocks and altered production values in tests. Use dedicated test environments and realistic fixtures.
