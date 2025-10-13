# Observability Integration Guide

This guide focuses on exposing Soma Fractal Memory metrics to Prometheus. Grafana dashboards are optional and not covered here.

## 1. Enable ServiceMonitor (recommended)

If your cluster runs the Prometheus Operator (kube-prometheus-stack, Openshift Monitoring, etc.), turn on the ServiceMonitor targets in `helm/values-production.yaml`:

```yaml
serviceMonitor:
  api:
    enabled: true
    labels:
      release: kube-prometheus-stack
  consumer:
    enabled: true
    labels:
      release: kube-prometheus-stack
```

This creates two ServiceMonitors:

- `somafractalmemory` scraping the API service (`/metrics` on port 9595)
- `somafractalmemory-consumer` scraping the consumer metrics endpoint (`/metrics` on port 8001)

If your monitoring stack expects the resources in a dedicated namespace, set `serviceMonitor.<component>.namespace` accordingly.

## 2. Fallback: scrape annotations

Clusters without the operator can rely on the provided scrape annotations. With the production values file the API and consumer Services expose:

```yaml
prometheus.io/scrape: "true"
prometheus.io/path: /metrics
prometheus.io/port: "<port>"
```

Point your Prometheus scrape configuration at the `somafractalmemory` Service (API) and `somafractalmemory-consumer-metrics` Service (consumer).

## 3. Alerts

Enable the built-in `PrometheusRule` manifest by setting `prometheusRule.enabled=true`. The default rules cover:

- API p95 latency (`api_request_latency_seconds_bucket` histogram)
- API 5xx ratio using the new `api_responses_total` counter
- Consumer processing failures (`consumer_process_failure_total`)
- Consumer stalls (no messages consumed in the configured window)

Example production overrides:

```yaml
prometheusRule:
  enabled: true
  labels:
    release: kube-prometheus-stack
  api:
    service: soma-memory-somafractalmemory
  consumer:
    service: soma-memory-somafractalmemory-consumer-metrics
```

Tune the thresholds under `prometheusRule.api.latency`, `.api.errorRate`, `.consumer.failureRate`, and `.consumer.stall` to match your SLOs.

Record the alert definitions and response playbooks in `docs/ops/PRODUCTION_RUNBOOK.md` once validated.

## 4. Verification checklist

- [ ] ServiceMonitor targets appear in Prometheus (`/targets` UI) and show `UP` status.
- [ ] Prometheus queries confirm API throughput/latency and consumer lag within SLOs.
- [ ] Alerts from the charted `PrometheusRule` trigger when test thresholds are breached.
- [ ] Evidence captured in `docs/PRODUCTION_READY_GAP.md` for the Observability row.

## 5. Shared infra health snapshot

Use `scripts/sharedinfra-health.sh` to capture a namespace summary that operators can attach to incidents or sprint evidence:

```bash
./scripts/sharedinfra-health.sh \
  --namespace soma-memory \
  --release soma-memory \
  --postgres-pod soma-memory-postgres-0 \
  --consumer-pod soma-memory-consumer-0
```

The script aggregates Helm status, pods, StatefulSets, PVCs, CronJobs, ExternalSecrets, ServiceMonitors, recent events, and optional Postgres readiness plus consumer metrics. Store the output in `docs/infra/sprints/sprint-3/sharedinfra-health.sample.log` (or similar) whenever you refresh evidence for Sprint 3.
