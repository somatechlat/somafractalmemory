# CI/CD: Deploy SomaStack

This repository includes a GitHub Actions workflow that builds the Docker image, scans Helm charts, and (optionally) deploys to Kubernetes with Helm.

## Workflow
- File: `.github/workflows/deploy-soma-stack.yml`
- Triggers:
  - Push to `master`
  - Manual dispatch with `deploy_mode`: `dev_full`, `dev_prod`, `prod`, or `prod_ha`

## Modes and values files
- `dev_full` → `helm/values-local-dev.yaml`
- `dev_prod` → `helm/values.yaml`
- `prod` → `helm/values.yaml`
- `prod_ha` → `helm/values-prod-ha.yaml`

## Image publishing
- Built with `docker/build-push-action` and pushed to `ghcr.io/<owner>/<repo>`
- Tags: `${{ github.sha }}` and `latest`
- Helm deploy overrides:
  - `--set image.repository=ghcr.io/<owner>/<repo>`
  - `--set image.tag=${{ github.sha }}`
  - `--set image.pullPolicy=Always`

## Global env
The helper script generates a unified env file per mode:

```bash
scripts/generate-global-env.sh <mode> [output_path]
```

Default output path: `.ci/soma-global.env` in the workspace. The workflow stores it at `${{ github.workspace }}/.ci/soma-global.env`.

## Kubernetes deploy
- Requires secret `KUBE_CONFIG` (base64 kubeconfig) to be set in repo secrets.
- Namespace pattern: `soma-<DEPLOY_MODE>`
- Release name: `soma`
- Basic validation waits for pods labeled `app=somafractalmemory` to be Ready.

## Local testing
You can generate the env locally:

```bash
scripts/generate-global-env.sh dev_full .ci/soma-global.env
```

Then run Helm lint locally (requires Helm installed):

```bash
helm lint ./helm
```

## Notes
- The workflow scans Helm with Trivy and fails on linting errors before deploy.
- Additional validations (metrics, tracing, mTLS) can be added once cluster observability endpoints are reachable from the runner.
