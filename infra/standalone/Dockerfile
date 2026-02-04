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
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /build

COPY pyproject.toml README.md /build/
COPY somafractalmemory /build/somafractalmemory

# Build a wheel reproducibly using build
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip build setuptools wheel \
    && python -m build --wheel --no-isolation -o /build/dist

# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME STAGE: slim image with only runtime deps and wheel installed
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /app

# System packages for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder stage and install
COPY --from=builder /build/dist /dist
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -d "/dist" ] && [ -n "$(ls -A /dist)" ]; then \
    pip install /dist/*.whl && \
    pip install "somafractalmemory[dev]"; \
    else \
    echo "No wheel files found"; exit 1; \
    fi

# Copy only essential runtime assets.
COPY manage.py /app/manage.py
COPY tests /app/tests
COPY conftest.py /app/conftest.py

# Also copy source tree to ensure latest local code is importable at runtime
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
    SOMA_MEMORY_MODE=evented_enterprise \
    DJANGO_SETTINGS_MODULE=somafractalmemory.settings.standalone

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${SOMAFRACTALMEMORY_PORT:-10101}/health" || exit 1

ENTRYPOINT ["uvicorn"]
CMD ["somafractalmemory.config.asgi:application", "--host", "0.0.0.0", "--port", "10101", "--workers", "1"]
