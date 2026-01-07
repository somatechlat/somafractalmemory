"""
SOMAFRACTALMEMORY - MINIKUBE + TILT
Uses existing Helm chart from infra/helm/
Namespace: somafractalmemory
ISOLATION: Port 10351 ONLY
PORTS: 10xxx namespace
"""
allow_k8s_contexts('minikube')


# Ensure namespace exists (idempotent)
local_resource(
    'create-namespace-somafractalmemory',
    cmd='kubectl create ns somafractalmemory --dry-run=client -o yaml | kubectl apply -f -',
    labels=['setup']
)

# Create dev secrets (idempotent, safe for dev)
local_resource(
    'create-secrets-somafractalmemory',
    cmd="""
    kubectl create secret generic soma-postgres-password --from-literal=SOMA_POSTGRES_PASSWORD=somapassword --from-literal=POSTGRES_PASSWORD=somapassword --from-literal=password=somapassword --from-literal=postgresql-password=somapassword -n somafractalmemory --dry-run=client -o yaml | kubectl apply -f -
    kubectl create secret generic soma-api-token --from-literal=SOMA_API_TOKEN=devtoken --from-literal=token=devtoken -n somafractalmemory --dry-run=client -o yaml | kubectl apply -f -
    """,
    labels=['setup']
)

# Apply strict dev limits (prod parity)
k8s_yaml('../somaAgent01/infra/k8s/shared/dev-limits.yaml')

# Use existing Helm chart - deployed to isolated namespace
k8s_yaml(helm(
    'infra/helm',
    name='somafractalmemory',
    namespace='somafractalmemory',
    values=['infra/helm/values-local-dev.yaml'],
))

# Docker build with live update
docker_build(
    'somafractalmemory',
    '.',
    dockerfile='Dockerfile',
    live_update=[sync('.', '/app')],
)

# Resource config with port forwards (names match Helm chart output)
k8s_resource('somafractalmemory-somafractalmemory', port_forwards=['10595:9595'], labels=['storage'])
k8s_resource('somafractalmemory-postgres', port_forwards=['10432:5432'], labels=['storage'])
k8s_resource('somafractalmemory-redis', port_forwards=['10379:6379'], labels=['storage'])

# Database migrations
local_resource(
    'sfm-migrations',
    cmd='kubectl exec -n somafractalmemory deploy/somafractalmemory-somafractalmemory -- python manage.py migrate --noinput 2>/dev/null || echo "Waiting for pod..."',
    resource_deps=['somafractalmemory-postgres', 'somafractalmemory-somafractalmemory'],
    labels=['setup'],
)
