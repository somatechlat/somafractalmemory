# soma-infra Helm Chart

This chart wraps the upstream Helm charts required by the SomaStack playbook:

- Bitnami `postgresql-ha` (includes Pgpool)
- Bitnami `redis`
- Bitnami `kafka`
- Hashicorp `vault`
- OPA upstream `opa`
- Prometheus Community `prometheus`
- Grafana `grafana`

`values.yaml` sets sensible defaults for Kind/local usage; environment overlays (`values-dev.yaml`, `values-test.yaml`, `values-staging.yaml`, `values-prod-lite.yaml`, `values-prod.yaml`) tune replica counts, persistence, and security.

Templates for service annotations/policies will be added next; for now, the chart consumes upstream defaults via values overrides.
