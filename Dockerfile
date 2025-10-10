# syntax=docker/dockerfile:1.6
# Development Dockerfile (uv-managed virtualenv) for API and consumer workflows
FROM python:3.10-slim AS base

ARG ENABLE_REAL_EMBEDDINGS=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        netcat-openbsd \
        procps \
    && rm -rf /var/lib/apt/lists/*

# Install uv once and place it on PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Copy minimal metadata to resolve dependencies before bringing the whole repo
COPY pyproject.toml uv.lock* requirements*.txt api-requirements*.txt /app/

RUN if [ "${ENABLE_REAL_EMBEDDINGS}" = "1" ]; then \
        EXTRAS="--extra api --extra events --extra hash-embeddings"; \
    else \
        EXTRAS="--extra api --extra events"; \
    fi && \
    if [ -f uv.lock ]; then \
        echo "Using uv.lock (frozen)"; \
        uv sync --frozen ${EXTRAS}; \
    else \
        echo "No uv.lock found; resolving"; \
        uv lock && uv sync ${EXTRAS}; \
    fi

# Copy application source and runtime assets
COPY somafractalmemory/ ./somafractalmemory/
COPY common/ ./common/
COPY src/somafractalmemory/ ./src/somafractalmemory/
COPY workers/ ./workers/
COPY eventing/ ./eventing/
COPY scripts/ ./scripts/
COPY langfuse/ ./langfuse/
COPY examples/ ./examples/
COPY docs/ ./docs/
COPY mkdocs.yml README.md CHANGELOG.md LICENSE ./

RUN chmod +x /app/scripts/docker-entrypoint.sh

# Create non-root user for runtime
RUN useradd --create-home --uid 1000 appuser && \
    chown -R appuser:appuser /app /opt/venv

USER appuser

ENV PATH="/opt/venv/bin:${PATH}"

# Expose HTTP API and gRPC ports (sync gRPC 50053, async gRPC 50054)
EXPOSE 9595 8001 50053 50054

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:9595/healthz || exit 1

CMD ["/app/scripts/docker-entrypoint.sh"]
