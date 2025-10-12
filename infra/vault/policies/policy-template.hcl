path "secret/data/shared-infra/${APP_NS}/${ENV}/*" {
  capabilities = ["read"]
}

path "secret/metadata/shared-infra/${APP_NS}/${ENV}/*" {
  capabilities = ["list", "read"]
}

path "auth/kubernetes/role/${APP_NS}" {
  capabilities = ["read"]
}
