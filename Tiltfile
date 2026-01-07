# SomaFractalMemory Tilt Development Configuration
# VIBE Rule 113: Port Sovereignty - 10xxx Range (Storage Tier L2)
# VIBE Rule 102: Shared-Nothing Architecture (Island Mandate)
# RAM BUDGET: 8GB Maximum (VIBE Rule 108)

print("""
+==============================================================+
|         SOMAFRACTALMEMORY - ISOLATED LOCAL DEVELOPMENT       |
+==============================================================+
|  Tilt Dashboard:   http://localhost:10353                    |
|  SFM API:          http://localhost:10101                    |
|  Postgres:         localhost:10432                           |
|  Redis:            localhost:10379                           |
|  Milvus:           localhost:10530                           |
+==============================================================+
|  RAM BUDGET: 8GB Maximum                                     |
+==============================================================+
""")

# Load existing docker-compose.yml infrastructure
# Port overrides applied via environment variables
docker_compose('./docker-compose.yml')

# Development server with live reload
local_resource(
    'sfm-dev',
    serve_cmd='SOMA_DB_NAME=somafractalmemory .venv/bin/uvicorn somafractalmemory.asgi:application --host 0.0.0.0 --port 10101 --reload',
    serve_dir='.',
    env={
        'SA01_DEPLOYMENT_MODE': 'PROD',
        'SOMA_API_PORT': '10101',
    },
    links=['http://localhost:10101/healthz'],
    labels=['app'],
    resource_deps=['postgres', 'redis', 'milvus'],
)

# Database migrations
local_resource(
    'db-migrate',
    cmd='''
        set -e
        set -a; source .env; set +a
        export DJANGO_SETTINGS_MODULE=somafractalmemory.settings
        echo "⏳ Waiting for Postgres on 10432..."
        until pg_isready -h localhost -p 10432; do sleep 1; done
        echo "🔄 Running migrations..."
        .venv/bin/python manage.py migrate --noinput
        echo "✅ Migrations complete"
    ''',
    resource_deps=['postgres'],
    labels=['setup'],
)
