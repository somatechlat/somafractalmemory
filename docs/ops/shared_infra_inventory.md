# Shared infra inventory (Somafractalmemory)

This document records the snapshot of the shared docker infra that lives on the
local Docker host (project `soma_docker_shared_infra`) and the minimal, safe
changes applied during the troubleshooting and remediation of the vector-store
(qdrant) routing.

> NOTE: The shared infra is a multi-service stack used by many projects. All
> modifications performed by this run were staged, reversible, and made with
> the explicit goal of avoiding service disruption. Do not remove core services
> (volumes or data) without operator agreement.

## Container snapshot (observed)

- somafractalmemory_qdrant_standalone — image: `qdrant/qdrant:latest` — host port `6333` → container `6333` — role: vector store (fallback)
- somafractalmemory_postgres — image: `postgres:16-alpine` — host port `5434` → container `5432`
- somafractalmemory_redis — image: `redis:7.2.4-alpine` — host port `6380` → container `6379`
- somafractalmemory_kafka — image: `apache/kafka:3.8.0` — host port `9096` → container `9092`
- somafractalmemory_grafana — image: `grafana/grafana:10.2.3` — host port `3131` → container `3000`
- somafractalmemory_prometheus — image: `prom/prometheus:v2.47.2` — host port `9095` → container `9090`
- somafractalmemory_quadrant — image: `caddy:2.8.4-alpine` — host port `8088` → container `8080` — role: HTTP gateway / reverse-proxy
- other supporting services: etcd, vault, opa, UI containers and kind nodes (see `docker ps` / `docker network inspect` for full list)

> The inventory above was inspected from the `soma_docker_shared_infra_soma-network`
> Docker network and the host published port mappings. The network attaches
> application containers (API + consumer) to the same internal namespace.

## Problem observed

- The application API (FastAPI) expected a vector-store backend (Qdrant) at
  `qdrant:6333`. During local testing the team had a `qdrant` standalone
  container, but the production-ish shared infra uses a gateway service
  `quadrant` (Caddy) which is capable of proxying to a Qdrant backend.
- The environment and routing between `quadrant` and `qdrant` were not wired in
  a way that made the vector-store available consistently for the API. A
  mismatch produced timeouts during `POST /store` when the API attempted
  end-to-end operations while eventing/lib callouts were also active.

## Changes applied (safe, reversible)

1. Added a runtime reverse-proxy route in the running `quadrant` container via
   the Caddy admin API (no host file edits were performed). The route maps
   `http://quadrant:8080/qdrant/...` → `http://qdrant:6333/...`. This was done
   via a JSON PATCH to `http://quadrant:2019/config` and is active immediately.

   JSON Patch (applied):

   ```json
   [
     {
       "op": "add",
       "path": "/apps/http/servers/srv0/routes/-",
       "value": {
         "handle": [
           {
             "handler": "subroute",
             "routes": [
               {
                 "handle": [
                   {"handler": "rewrite", "uri": {"strip_prefix": "/qdrant"}},
                   {"handler": "reverse_proxy", "upstreams": [{"dial": "qdrant:6333"}]}
                 ],
                 "match": [{"path": ["/qdrant/*"]}]
               }
             ]
           }
         ]
       }
     }
   ]
   ```

   The patch is runtime-only and does not modify the host `Caddyfile` that is
   bind-mounted into the container. For persistence, add an equivalent route to
   the host's Caddyfile (see `Persistence & cleanup` below).

2. Alternate routing via the canonical compose (recommended)

Rather than maintain multiple overlay files, the repository uses a single
`docker-compose.yml` that supports profiles and environment overrides. To
point the API and consumers at an alternate Qdrant route (for example a
quadrant/Caddy proxy), prefer supplying `QDRANT_URL` when you start the
services or create a small single-file override that is clearly documented.

Examples:

```bash
# Start shared infra
docker compose --profile shared up -d

# Start API + consumer and override Qdrant at runtime
QDRANT_URL="http://quadrant:8080/qdrant" docker compose up -d api somafractalmemory_kube
```

If you need a reproducible override for your team, commit a small override
file (one purpose only) and document it in the repo. Avoid multiple, long-
living overlays that diverge from the canonical compose file.

3. Eventing

The recommended practice is to run tests and E2E flows against real eventing
backends. Use `EVENTING_ENABLED=false` or isolated overrides only for
developer experiments; prefer enabling the real broker for integration tests.

## Verification performed

- Queried the running Caddy config (admin API) to ensure the `/qdrant` route
  is present.
Recreated the API container using a short-lived override (now migrated to the canonical profile-based approach)
  and verified the API `QDRANT_URL` resolves to the `quadrant` proxy.
- Performed in-network health and metrics checks against the API and direct
  Qdrant checks via the `quadrant` route to ensure the vector store is
  reachable and the default collection exists.

## Persistence & cleanup (recommended)

- Make the `quadrant` change persistent by adding an equivalent route to the
  host Caddyfile that is bind-mounted into the container at
  the host path used by the infra repository: e.g.

  ```caddy
  :8080 {
    handle_path /qdrant/* {
      uri strip_prefix /qdrant
      reverse_proxy qdrant:6333
    }
    # other existing routes...
  }
  ```

  The host `Caddyfile` discovered earlier sits outside this repository
  (example host path detected: `/Users/<user>/.../infra/docker/quadrant/Caddyfile`).
  Update the host file and then restart the quadrant service if you want the
  config to survive container restarts.

- Once the `quadrant` route is persisted and validated for the observation
  window (recommended: 10–30 minutes), optionally stop and remove the
  `soma_docker_shared_infra-qdrant-standalone` container. Keep its volumes
  (data) in place until you confirm no additional data recovery is needed.

## Rollback steps

- To revert routing immediately: remove the `/qdrant` runtime route via the
  Caddy admin API (use a JSON Patch `op: remove` against
  `/apps/http/servers/srv0/routes/<index>` where `<index>` is the appended
  route index) or restart quadrant with the original host `Caddyfile`.
- To return API & consumer to direct `qdrant:6333` behavior, stop the
  containers created with a temporary override and
  recreate them with the original compose command (omit the override).

## Files & overrides

No long-lived override files are maintained in this repository. The recommended
approach is to use the canonical `docker-compose.yml` with Compose profiles or
small, single-purpose overrides documented in this repo when necessary. This
keeps the main compose file as the single source of truth and prevents drift.

## Notes & operational cautions

- The Caddy admin API listens on port 2019. The quadrant instance in this
  deployment is reachable on the host port `2033` → container `2019`.
  Be cautious when exposing admin endpoints in production contexts.
- All changes documented here are reversible. Do not delete data volumes.
