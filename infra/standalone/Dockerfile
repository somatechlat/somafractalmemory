# ═══════════════════════════════════════════════════════════════════════════════
# 🚨 STANDALONE DEPLOYMENT: COLIMA + TILT + MINIKUBE 🚨
# ═══════════════════════════════════════════════════════════════════════════════
# This project uses:
#   ✅ COLIMA   - Docker runtime (NOT Docker Desktop)
#   ✅ TILT     - Development orchestration
#   ✅ MINIKUBE - Kubernetes cluster
#
# ❌ DO NOT USE DOCKER DESKTOP
# ❌ DO NOT USE docker-compose directly
#
# Start with: tilt up --port <port>
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# PYTHON BUILDER STAGE: Build Python wheel
# ═══════════════════════════════════════════════════════════════════════════════
## Clean multi-stage Dockerfile: build wheel from pyproject and install in slim runtime
### Builder stage: build wheel
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /build

COPY pyproject.toml README.md /build/
COPY somafractalmemory /build/somafractalmemory
COPY common /build/common

# Build a wheel reproducibly using build
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip build setuptools wheel \
    && python -m build --wheel --no-isolation -o /build/dist

### Runtime stage: slim image with only runtime deps and wheel installed
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /app

# System packages for healthcheck and optional components
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl supervisor python3-numpy \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder stage and install
COPY --from=builder /build/dist /dist
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -d "/dist" ] && [ -n "$(ls -A /dist)" ]; then pip install /dist/*.whl; else echo "No wheel files found"; exit 1; fi

# Install gunicorn for Django production
RUN --mount=type=cache,target=/root/.cache/pip pip install gunicorn

# Copy only essential runtime assets.
COPY manage.py /app/manage.py
COPY common /app/common

# Also copy source tree to ensure latest local code is importable at runtime (overrides wheel)
COPY somafractalmemory /app/somafractalmemory

# Ensure runtime imports from /app are visible
ENV PYTHONPATH=/app:${PYTHONPATH:-}

# Prepare writable log dir
RUN mkdir -p /app/logs && chmod 0755 /app/logs

# Create non-root user with UID/GID 1000
RUN set -eux; \
    if ! getent group 1000 >/dev/null; then groupadd -g 1000 appuser; fi; \
    if ! id -u 1000 >/dev/null 2>&1; then useradd --create-home -u 1000 -g 1000 --shell /usr/sbin/nologin appuser; fi; \
    chown -R 1000:1000 /app
USER 1000:1000

# Expose default API port
EXPOSE 10101

# Environment defaults
ENV SOMAFRACTALMEMORY_HOST=0.0.0.0 \
    SOMAFRACTALMEMORY_PORT=10101 \
    SOMAFRACTALMEMORY_WORKERS=1 \
    SOMA_MEMORY_MODE=evented_enterprise

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${SOMAFRACTALMEMORY_PORT:-10101}/health" || exit 1

ENTRYPOINT ["python", "manage.py", "runserver", "0.0.0.0:10101"]
