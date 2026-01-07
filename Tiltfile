# ═══════════════════════════════════════════════════════════════════════════════
# 🚨 ARCHITECTURE: COLIMA + TILT + MINIKUBE 🚨
# ═══════════════════════════════════════════════════════════════════════════════
# SomaFractalMemory Tilt Development Configuration
# VIBE Rule 113: Port Sovereignty - 10xxx Range (Storage Tier L2)
# VIBE Rule 102: Shared-Nothing Architecture (Island Mandate)
# RAM BUDGET: 8GB Maximum (VIBE Rule 108)
# ═══════════════════════════════════════════════════════════════════════════════

print("""
+==============================================================+
|         SOMAFRACTALMEMORY - ISOLATED K8S DEPLOYMENT          |
+==============================================================+
|  Tilt Dashboard:   http://localhost:10353                    |
|  SFM API:          http://localhost:10101 (NodePort 30101)   |
|  Minikube Profile: sfm                                       |
+==============================================================+
|  RAM BUDGET: 8GB Maximum | ARCHITECTURE: Colima+Tilt+Minikube|
+==============================================================+
""")

# Ensure we're using the sfm minikube profile
allow_k8s_contexts('sfm')

# Build the SFM API image
docker_build(
    'sfm-api',
    '.',
    dockerfile='Dockerfile',
    live_update=[
        sync('.', '/app'),
        run('pip install -r api-requirements.txt', trigger=['api-requirements.txt']),
    ]
)

# Deploy resilient K8s manifests
k8s_yaml('infra/k8s/sfm-resilient.yaml')

# Resource configuration with port forwards
k8s_resource(
    'sfm-api',
    port_forwards=['10101:10101'],
    labels=['app'],
    resource_deps=['postgres', 'redis', 'milvus']
)

k8s_resource(
    'postgres',
    port_forwards=['10432:5432'],
    labels=['infra']
)

k8s_resource(
    'redis',
    port_forwards=['10379:6379'],
    labels=['infra']
)

k8s_resource(
    'milvus',
    port_forwards=['10530:19530'],
    labels=['infra']
)

# Migration job
k8s_resource(
    'sfm-migrations',
    labels=['setup'],
    resource_deps=['postgres']
)
