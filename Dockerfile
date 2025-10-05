# syntax=docker/dockerfile:1
# Minimal Dockerfile to run the FastAPI example
FROM python:3.10-slim

# Build args to control installed dependencies
ARG ENABLE_REAL_EMBEDDINGS=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (build tools and curl for health/metrics checks)
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# Install netcat for scripts that need to probe other containers
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Install procps to provide sysctl binary for adjusting kernel parameters inside containers
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*
# Install uv and verify it
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    /root/.local/bin/uv --version

# Copy the repository (source, scripts, pyproject)
COPY . /app

# Use uv to create a virtual environment and install project dependencies with extras.
# Always include API and events; include hash-embeddings when requested by build arg.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN if [ "${ENABLE_REAL_EMBEDDINGS}" = "1" ]; then \
            EXTRAS="--extra api --extra events --extra hash-embeddings" ; \
        else \
            EXTRAS="--extra api --extra events" ; \
        fi && \
        if [ -f uv.lock ]; then \
            echo "Using uv.lock (frozen)"; \
            /root/.local/bin/uv sync --frozen $EXTRAS; \
        else \
            echo "No uv.lock found; resolving and creating a new lock"; \
            /root/.local/bin/uv lock && /root/.local/bin/uv sync $EXTRAS; \
        fi

COPY . /app

RUN chmod +x /app/scripts/docker-entrypoint.sh

EXPOSE 9595 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:9595/healthz || exit 1

# Default command (API entrypoint) – can be overridden by docker compose for consumer etc.
ENV PATH="/opt/venv/bin:${PATH}"
CMD ["/app/scripts/docker-entrypoint.sh"]
