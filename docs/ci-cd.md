# CI/CD: Deploy Soma Fractal Memory

This repository ships a GitHub Actions workflow at `.github/workflows/deploy-soma-stack.yml` that can:

- Build and push the Docker image to GHCR
- Lint the Helm chart and run a Trivy filesystem scan
- Optionally deploy to a Kubernetes cluster via Helm
- Perform basic validation (pods Ready, basic health check)

## Modes

Choose a deployment mode via workflow dispatch input `deploy_mode`:

- dev_full → uses `helm/values-local-dev.yaml`
- dev_prod → uses `helm/values.yaml`
- prod → uses `helm/values.yaml`
- prod_ha → uses `helm/values-prod-ha.yaml`

## Required secrets

Add these repository secrets if you want to deploy to a cluster:

- `KUBE_CONFIG` (string or base64): kubeconfig content for the target cluster
- `SOMA_API_TOKEN`: API token to inject into the release secret
- `POSTGRES_PASSWORD`: Postgres password used by the app

Notes:
- `GITHUB_TOKEN` is provided by Actions and is used to push to GHCR.
- If `KUBE_CONFIG` is not set, the workflow will still build/push the image and lint/scan, but will skip deployment and validations.

## Helper script

`scripts/generate-global-env.sh` produces a unified environment file based on the chosen mode. The workflow calls it automatically; you can run it locally too:

```
./scripts/generate-global-env.sh dev_full .ci/soma-global.env
```

## Labels and selectors

The Helm chart applies the label `app=somafractalmemory` to pods. Validation uses this label to wait for readiness.

## Rollback

If deployment or validation fails, the workflow attempts a `helm rollback` to the previous revision for the same release/namespace.

## Local smoke test

- Lint the chart:
  - `helm lint ./helm`
- Render templates:
  - `helm template soma ./helm -f helm/values-local-dev.yaml | head`
