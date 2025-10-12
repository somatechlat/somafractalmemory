# Scripts Index

This document lists the operational scripts in `scripts/` and when to use them. Make is the canonical interface for day-to-day tasks; scripts are used under-the-hood or for targeted operations.

- run_consumers.py: Start the Kafka consumers locally (Compose). Exposes Prometheus metrics on :8001. Used by `docker-compose.yml` consumer profile.
- start_stack.sh: Bring up the canonical evented stack (Kafka + Postgres + Qdrant). Prefer `make setup-dev` for the full Compose stack.
- generate_openapi.py: Refresh the `openapi.json` file (generated). Prefer generating during docs build in CI.
- generate_protos.py: Regenerate gRPC stubs from `proto/memory.proto`.
- run_server.sh / start_all.sh / start-dual-servers.sh: Legacy helpers for manual starts; prefer `make` and Docker Compose.
- port_forward_api.sh / reliable_port_forward.sh: Port-forward helper scripts for Kubernetes clusters when not using NodePort/Ingress.
- synthetic_real_stack_benchmark.py: Run synthetic end-to-end benchmarks against a live API.
- verify_full_stack.py / run_ci.sh / run_docker_ci.sh: CI helpers.

For shared Kubernetes infrastructure onboarding (reset → bootstrap → infra deploy → app wire-up → CD → verification), follow the canonical playbook appended to `docs/ROADMAP.md`.
