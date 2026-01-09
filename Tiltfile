# ═══════════════════════════════════════════════════════════════════════════════
# 🚨 ARCHITECTURE: TILT + MINIKUBE (VFKIT) + KUBERNETES 🚨
# ═══════════════════════════════════════════════════════════════════════════════
# SomaFractalMemory Tilt Development Configuration
# VIBE Rule 113: Port Sovereignty - 10xxx Range (Storage Tier L2)
# VIBE Rule 102: Shared-Nothing Architecture (Island Mandate)
# RAM BUDGET: 5GB Maximum (VIBE Rule 108 - Ultra Lean)
# ═══════════════════════════════════════════════════════════════════════════════

print("""
+==============================================================+
|         SOMAFRACTALMEMORY - ISOLATED K8S DEPLOYMENT          |
+==============================================================+
|  Tilt Dashboard:   http://localhost:10353                    |
|  SFM API:          http://localhost:10101 (NodePort 30101)   |
|  Minikube Profile: sfm                                       |
+==============================================================+
|  RAM BUDGET: 5GB Maximum | ARCHITECTURE: Tilt+Minikube(vfkit)+K8s|
+==============================================================+
""")

# Ensure we're using the sfm minikube profile
allow_k8s_contexts('sfm')

# Build using Minikube's image build (vfkit driver compatible)
custom_build(
    'sfm-api',
    'minikube image build -p sfm -t $EXPECTED_REF -f Dockerfile.api .',
    ['.'],
    live_update=[
        sync('.', '/app'),
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
