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

DOCKERFILE_CONTENT = '''
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r api-requirements.txt
EXPOSE 10101
CMD ["python", "manage.py", "runserver", "0.0.0.0:10101"]
'''

# Build using Minikube's internal Docker daemon (vfkit driver)
custom_build(
    'sfm-api',
    'eval $(minikube docker-env -p sfm) && printf "%s" "$DOCKERFILE_CONTENT" | docker build -t $EXPECTED_REF -f - .',
    ['.'],
    env={'DOCKERFILE_CONTENT': DOCKERFILE_CONTENT},
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
