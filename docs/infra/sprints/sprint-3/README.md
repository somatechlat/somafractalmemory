# Sprint 3 — Observability & CI (In Progress)

This folder captures artefacts for Sprint 3 deliverables defined in `docs/ARCHITECTURE_ROADMAP.md`.

## Deliverables (current status)
- ✅ `scripts/sharedinfra-health.sh` collects a namespace snapshot (Helm status, pods, PVCs, ServiceMonitors, Postgres readiness, consumer metrics).
- ✅ HTTP API, gRPC servers, workers, and consumer CLI now emit structured JSON logs via `common/utils/logger.py`.
- ✅ OpenTelemetry tracer bootstrap is centralised through `common/utils/trace.py` with structured logging on failure paths.
- ☐ GitHub Actions deployment workflow with readiness gates.
- ☐ Structured tracing exported to Jaeger in staging.
- ☐ Prometheus alert rule evidence (enable `prometheusRule.enabled` and capture firing proof; Grafana optional).

## Evidence to attach
- `sharedinfra-health.sample.log`: output from running `scripts/sharedinfra-health.sh --namespace <ns> --release <name>` against a target cluster.
- Log excerpts from API / consumer pods showing JSON structured fields (`service`, `component`, `event`).
- Prometheus query screenshots or CLI outputs illustrating alert thresholds (Grafana optional).
- GitHub Actions run URLs once the deployment workflow is implemented.

Add new artefacts to this folder as work completes. Update the checklist above so `docs/ARCHITECTURE_ROADMAP.md` and `docs/PRODUCTION_READY_GAP.md` stay in sync with evidence.
