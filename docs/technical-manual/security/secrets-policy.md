---
title: "Secrets Management Policy"
purpose: "- **Source of truth**: Secrets are stored in the platform secret manager (Vault in production, Kubernetes secrets in staging)."
audience:
  - "Operators and SREs"
last_updated: "2025-10-16"
---

# Secrets Management Policy

- **Source of truth**: Secrets are stored in the platform secret manager (Vault in production, Kubernetes secrets in staging). No secrets are committed to Git.
- **Required secrets**:
  - `SOMA_API_TOKEN`
  - `SOMA_POSTGRES_URL`
  - `SOMA_RATE_LIMIT_MAX` (optional override)
  - `SOMA_RATE_LIMIT_WINDOW_SECONDS`
- **Rotation**: API tokens rotate quarterly or immediately after any security incident. Update the secret store and redeploy using Helm.
- **Access**: Only members of the Platform and Security groups can read production secrets. Onboarding requires sign-off recorded in the access log.
- **Distribution**: Runtime pods mount secrets as environment variables or files. The HTTP API reads tokens via `_load_api_token()` which accepts either method.
- **Auditing**: Run `scripts/audit-docs.py` monthly to confirm documentation lists the current secret set. Monitor access logs for secret reads outside deploy windows.
