# Vault Policy Templates

- `policy-template.hcl` — base template used by `scripts/generate-sharedinfra-secrets.sh` to create per-namespace policies.
- Rendered policies are stored in this directory as `${APP_NS}.hcl` and can be applied via:
  ```sh
  vault policy write ${APP_NS} infra/vault/policies/${APP_NS}.hcl
  ```
  Ensure the `APP_NS` service account matches the Kubernetes namespace and service account name configured for the workload.
