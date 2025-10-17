---
title: "RBAC Matrix"
purpose: "| Role | Permissions | Notes | |------|-------------|-------| | `sfm-admin` | Manage deployments, rotate secrets, access `/metrics`, read/write `/memories`."
audience:
  - "Operators and SREs"
last_updated: "2025-10-16"
---

# RBAC Matrix

| Role | Permissions | Notes |
|------|-------------|-------|
| `sfm-admin` | Manage deployments, rotate secrets, access `/metrics`, read/write `/memories`. | Restricted to platform on-call engineers. |
| `sfm-operator` | Read `/stats`, `/health*`, `/metrics`; no write access to `/memories`. | Used by monitoring automation. |
| `sfm-client` | Invoke `/memories` routes with bearer token. | Issued to trusted downstream services. |
| `sfm-auditor` | Read-only access to logs, Prometheus, and documentation. | Used during compliance reviews. |

All service accounts must be bound to Kubernetes Roles that map to the scopes above. Tokens for external clients are managed by the secrets policy.
