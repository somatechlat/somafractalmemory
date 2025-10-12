#!/usr/bin/env bash
# Render Vault policy and ExternalSecret manifests for a given application namespace.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/generate-sharedinfra-secrets.sh <app-namespace> [env]

Example:
  scripts/generate-sharedinfra-secrets.sh sa01 dev

Requires:
  - envsubst (gettext)
  - templates in infra/vault/policies/policy-template.hcl
    and infra/external-secrets/externalsecret-template.yaml
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

APP_NS="${1:-}"
ENV="${2:-dev}"

if [[ -z "$APP_NS" ]]; then
  echo "Error: application namespace is required." >&2
  usage
  exit 1
fi

if ! command -v envsubst >/dev/null 2>&1; then
  echo "Error: envsubst not found (install gettext)." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POLICY_TEMPLATE="${REPO_ROOT}/infra/vault/policies/policy-template.hcl"
POLICY_OUTPUT="${REPO_ROOT}/infra/vault/policies/${APP_NS}.hcl"

EXT_TEMPLATE="${REPO_ROOT}/infra/external-secrets/externalsecret-template.yaml"
EXT_OUTPUT="${REPO_ROOT}/infra/external-secrets/${APP_NS}-externalsecret.yaml"

if [[ ! -f "$POLICY_TEMPLATE" ]]; then
  echo "Policy template missing at ${POLICY_TEMPLATE}" >&2
  exit 1
fi

if [[ ! -f "$EXT_TEMPLATE" ]]; then
  echo "ExternalSecret template missing at ${EXT_TEMPLATE}" >&2
  exit 1
fi

export APP_NS ENV

echo "Rendering Vault policy -> ${POLICY_OUTPUT}"
envsubst < "$POLICY_TEMPLATE" > "$POLICY_OUTPUT"

echo "Rendering ExternalSecret -> ${EXT_OUTPUT}"
envsubst < "$EXT_TEMPLATE" > "$EXT_OUTPUT"

cat <<EOF

Generated artefacts:
  - ${POLICY_OUTPUT}
  - ${EXT_OUTPUT}

Apply steps:
  vault policy write ${APP_NS} ${POLICY_OUTPUT}
  vault write auth/kubernetes/role/${APP_NS} \\
    bound_service_account_names=${APP_NS}-sa \\
    bound_service_account_namespaces=${APP_NS} \\
    policies=${APP_NS} \\
    ttl=24h
  kubectl apply -f ${EXT_OUTPUT}
EOF
