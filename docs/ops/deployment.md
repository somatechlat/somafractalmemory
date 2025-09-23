# Deployment Guide for SomaFractalMemory (Phase 3)

This guide explains how to deploy the unified **FastAPI + consumer** container built from `Dockerfile.single` and how to run the development stack locally.

## Prerequisites
- Docker ≥ 20.10 installed.
- (Optional) `docker compose` for the local development services defined in `docker-compose.dev.yml`.
- Environment variables for the services (see **Configuration** below).

## Building the Image
```bash
# From the repository root
docker build -f Dockerfile.single -t soma-fractal-memory:latest .
```
The multi‑stage Dockerfile installs all runtime dependencies and copies the `start_all.sh` script which launches:
1. The FastAPI server (`uvicorn examples.api:app`).
2. The Kafka consumer (`scripts/run_consumers.py`).
Both processes run in the same container and expose their Prometheus metrics on the same HTTP port.

## Running the Container
```bash
# Example run (replace env vars as needed)
docker run -d \
  -p 9595:9595 \   # FastAPI HTTP API
  -p 8001:8001 \   # Prometheus metrics (same port, /metrics path)
  -e KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
  -e KAFKA_MEMORY_EVENTS_TOPIC=memory.events \
  -e CONSUMER_METRICS_PORT=8001 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_PORT=5433 \
  -e POSTGRES_DB=soma \
  -e POSTGRES_USER=soma \
  -e POSTGRES_PASSWORD=soma \
  -e QDRANT_HOST=host.docker.internal \
  -e QDRANT_PORT=6333 \
  soma-fractal-memory:latest
```
The container will start both processes and keep running until one exits. The `ENTRYPOINT` is `/app/start_all.sh` which handles process supervision.

## Local Development Stack
For local development you can spin up the required services with the provided compose file:
```bash
./scripts/start_stack.sh development --with-broker
```
This brings up:
- **Redpanda** (Kafka compatible broker) on `localhost:9092`
- **Apicurio Registry** on `localhost:8080`
- **PostgreSQL** on `localhost:5433`
- **Qdrant** on `localhost:6333`
After the stack is running, start the unified container as shown above, pointing the environment variables to `localhost`.

## Configuration (Environment Variables)
| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka/Redpanda broker address |
| `KAFKA_MEMORY_EVENTS_TOPIC` | `memory.events` | Topic name for memory events |
| `KAFKA_CONSUMER_GROUP` | `soma-consumer-group` | Consumer group identifier |
| `CONSUMER_METRICS_PORT` | `8001` | Port on which `/metrics` is served |
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_DB` | `soma` |
| `POSTGRES_USER` | `soma` |
| `POSTGRES_PASSWORD` | `soma` |
| `QDRANT_HOST` | `localhost` |
| `QDRANT_PORT` | `6333` |
| `SOMA_API_TOKEN` | (optional) | Token required for FastAPI auth |

## Observability
- **API metrics** are exposed at `http://<host>:9595/metrics` (via FastAPI instrumentation).
- **Consumer metrics** share the same endpoint (`/metrics`) because the same Prometheus client instance is used in both processes.
- Use Prometheus or Grafana to scrape `http://<host>:8001/metrics`.

## Stopping the Service
```bash
# Stop the Docker container
docker ps    # find the container ID
docker stop <container-id>
```
The `start_all.sh` script forwards the `SIGTERM` signal to both child processes, ensuring a graceful shutdown.

---
*This document is part of Phase 3 – production‑ready deployment.*
