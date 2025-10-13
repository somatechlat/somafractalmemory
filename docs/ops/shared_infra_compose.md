# Running somafractalmemory With the Shared Docker Infrastructure

This guide walks through starting the local `somafractalmemory` services while reusing the company-wide Docker Compose environment (Postgres, Redis, Kafka, Qdrant, etc.). Follow the steps in order so your containers join the existing network rather than starting duplicate infrastructure.

## Prerequisites
-- Shared Docker stack is running and exposes the external network `Somafractalmemory_docker_shared_infra_soma-network`.
- You have access to the repository root (`somafractalmemory/`).
- Docker Compose v2 is available (`docker compose` command).

> Tip: use `docker ps --filter "name=Somafractalmemory"` to confirm the shared containers are healthy before proceeding.

## 1. Attach to the repository
```bash
cd /path/to/somafractalmemory
```

## 2. Verify the shared network is visible
```bash
docker network inspect Somafractalmemory_docker_shared_infra_soma-network >/dev/null
```
The compose file references this external network via the `soma_shared` alias. If the command fails, start the shared stack first or ask the platform team for assistance.

## 3. Launch the API service
```bash
docker compose up -d api
```
This builds (if needed) and starts `somafractalmemory_api`, wiring it to the shared Redis/Postgres/Kafka/Qdrant endpoints. The compose file limits Uvicorn to a single worker to avoid duplicate schema initialization against the shared Postgres instance.

Check the container health:
```bash
docker ps --filter name=somafractalmemory_api
```
The `STATUS` column should include `(healthy)` once startup completes.

## 4. (Optional) Launch the Kafka consumers
Only start these when you need event processing:
```bash
docker compose --profile consumer up -d
```
This brings up the `somafractalmemory_kube` workers on the same shared network. Leave the `--profile consumer` flag out when you only want the HTTP API.

## 5. Smoke-test the API
```bash
curl -sf http://localhost:9595/healthz
```
A JSON response with `"kv_store": true` indicates Postgres connectivity. If Kafka is still starting you may see `"vector_store": false`; rerun the check once the upstream service is ready.

## 6. Tear down when finished
```bash
docker compose down
```
Use `docker compose --profile consumer down` if the consumer profile was enabled. This stops only the project containers, leaving the shared infrastructure untouched.

## Troubleshooting
- **Kafka warm-up:** The entrypoint waits up to 30 seconds for `kafka:9092`. If Kafka stays in `starting` state, the API will still boot but publish features may be degraded until Kafka is healthy.
- **Network not found:** Ensure `Somafractalmemory_docker_shared_infra_soma-network` exists; the shared stack must be running, or you can create an empty bridge network with that name temporarily.
- **Schema conflicts:** The compose file now uses `UVICORN_WORKERS=1` so only a single process initializes the Postgres schema, avoiding duplicate type creation errors on the shared database.
