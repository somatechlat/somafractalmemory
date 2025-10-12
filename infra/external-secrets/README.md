Templates for ExternalSecret resources that wire application namespaces to Vault-stored credentials.

- `externalsecret-template.yaml` — render with `scripts/generate-sharedinfra-secrets.sh APP_NS ENV`.
- Generated manifests land in this directory as `${APP_NS}-externalsecret.yaml` and should be applied via `kubectl apply -f`.
