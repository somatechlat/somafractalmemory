# Roadmap
# Roadmap

This roadmap reflects the current codebase and deployment assets.

## Near‑term

- Documentation hygiene
    - Keep docs aligned with code: this pass removed stale pages/links and updated README, index, mkdocs nav.
- Stability fixes
    - core: import psycopg2.sql helpers, fix logging NameError in embed_text
    - http_api: removed duplicate helpers; keep single configuration path
    - Dockerfile: remove repeated transformers installs
- CI & testing
    - Add a minimal CI to run `ruff`, `mypy`, `pytest -q` on PRs
    - Add workflow to build API image and run a Compose health check
- Observability
    - Ensure `/metrics` is scraped in local/helm profiles; document Grafana dashboards
- Helm chart
    - Validate chart with `helm lint` and kind; harmonize Kafka image/vars with Compose or document differences

## Performance & features

- Fast Core slab index on by flag: benchmark vs Qdrant only
- Hybrid recall: add Postgres JSONB text index path to reduce scan costs for keyword boosts on large datasets
- Eventing: wire background workers (consumers) for WAL reconciliation/indexing

## Production hardening


## Longer‑term

- Multi‑modal payload support (structured metadata + vector embeddings)
- Pluggable graph backends (e.g., Neo4j) behind `IGraphStore`
- Federated/tenant isolation for namespaces and quotas
