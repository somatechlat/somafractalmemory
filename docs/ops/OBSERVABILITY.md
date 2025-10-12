# Observability Integration Guide

This guide explains how to scrape Soma Fractal Memory metrics with Prometheus and surface them in Grafana.

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

## 3. Grafana dashboards

Import dashboards or create new ones using the following query starters:

- API request latency: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{app_kubernetes_io_name="somafractalmemory"}[5m])) by (le, route))`
- Error rate: `sum(rate(fastapi_requests_total{status="500", app_kubernetes_io_name="somafractalmemory"}[5m]))`
- Consumer throughput: `sum(rate(consumer_messages_consumed_total{app_kubernetes_io_component="consumer"}[5m]))`
- Qdrant failures: `sum(rate(consumer_process_failure_total{component="vector_indexer"}[5m]))`

Store final dashboards under `docs/ops/dashboards/` (JSON exports) and link them in this guide.

## 4. Alerts

Define PrometheusRule resources (outside this chart for now) covering:

- Elevated API 5xx rate (p95 latency + error ratio)
- Consumer backlog / stalled processing (low throughput, high failure counts)
- Backup CronJob failures (CronJob status metrics)

Record the alert rule links and on-call runbooks in `docs/ops/PRODUCTION_RUNBOOK.md` when available.

## 5. Verification checklist

- [ ] ServiceMonitor targets appear in Prometheus (`/targets` UI) and show `UP` status.
- [ ] Dashboards display live metrics for API and consumer pods.
- [ ] Alerts trigger when test thresholds are breached.
- [ ] Evidence captured in `docs/PRODUCTION_READY_GAP.md` for the Observability row.
