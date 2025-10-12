# Consuming Existing Shared Infra Containers

When the shared SomaStack infrastructure is already running on a host (Redis, Postgres/Pgpool, Kafka, Vault, etc.), do **not** start the local development copies defined in `docker-compose.yml`. Instead, point the SFM services at the existing containers.

## 1. Identify available services

```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
```

Look for containers such as:

- `sharedinfra-postgres`, `sharedinfra-postgres-pgpool`
- `sharedinfra-redis-master` / replicas
- `sharedinfra-kafka`
- `sharedinfra-vault`
- `sharedinfra-opa`, `sharedinfra-prometheus`, `sharedinfra-grafana`

Record their exposed host ports or DNS names.

## 2. Export connection endpoints

Update your shell session (or `.env` file) so the SFM services reference the shared infra instead of local containers. Two options are available.

### Option A — native SFM settings (`SOMA_` prefix)

```bash
export SOMA_INFRA__REDIS=sharedinfra-redis-master.soma-infra.svc.cluster.local
export SOMA_INFRA__POSTGRES=sharedinfra-postgres-pgpool.soma-infra.svc.cluster.local
export SOMA_INFRA__QDRANT=sharedinfra-qdrant.soma-infra.svc.cluster.local
export SOMA_INFRA__KAFKA=sharedinfra-kafka.soma-infra.svc.cluster.local:9092
export SOMA_INFRA__VAULT=sharedinfra-vault.soma-infra.svc.cluster.local:8200
```

### Option B — direct environment variables consumed by `docker-compose.yml`

```bash
export REDIS_HOST=sharedinfra-redis-master
export REDIS_PORT=6379
export POSTGRES_URL=postgresql://soma:password@sharedinfra-postgres-pgpool:5432/somamemory
export QDRANT_HOST=sharedinfra-qdrant
export QDRANT_PORT=6333
export KAFKA_BOOTSTRAP_SERVERS=sharedinfra-kafka:9092
```

Whichever option you use, ensure credentials (passwords, TLS certificates) match the shared environment. Pull them from Vault or the automation scripts provided by the infra team.

## 3. Start only application services

Avoid launching the shared infra services defined in `docker-compose.yml`. Either:

- Run just the services you need:

  ```bash
  docker compose up -d api somafractalmemory_kube
  ```

- Or introduce a profile to the compose command:

  ```bash
  COMPOSE_PROFILES=app docker compose up -d
  ```

  (Add `profiles: ["infra"]` to shared infra services if you want a persistent toggle.)

## 4. Verify connectivity

```bash
# API health should succeed against shared infra endpoints
curl -fsS http://localhost:9595/healthz | jq .

# Ensure Kafka connectivity
docker compose logs -f somafractalmemory_consumer
```

If the API or consumer fails to connect, check environment variables, network reachability, and firewall rules.

## 5. Automation scripts

- `scripts/reset-sharedinfra-compose.sh` — use on the machine hosting the shared infra to reset containers and volumes before a clean deploy.
- `scripts/deploy-kind-sharedinfra.sh` — recreates shared infra on Kind; skip this when consuming an existing Docker-based shared environment.

Keep these steps in sync with the architecture roadmap (Sprint 0/1) so everyone reuses the shared resources instead of starting duplicates.
