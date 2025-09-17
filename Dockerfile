# syntax=docker/dockerfile:1.6

ARG PYTHON_VERSION=3.11

################################
# Builder: install deps + tests
################################
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy minimal metadata first for better layer caching
COPY pyproject.toml README.md requirements.txt ./
COPY src ./src
COPY tests ./tests

RUN python -m pip install --upgrade pip setuptools wheel build \
 && pip install -e '.[dev]' \
 && pip install -r requirements.txt

# Build a wheel artifact for the runtime stage
RUN python -m build --wheel --outdir /dist

# Run tests inside builder to validate the wheel (install dev extras already installed)
RUN pytest -q

##############################
# Runtime: minimal install
##############################
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy the built wheel from the builder stage and install it in the runtime image
COPY --from=builder /dist /dist
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install /dist/*.whl

LABEL org.opencontainers.image.title="somafractalmemory" \
      org.opencontainers.image.description="Modular memory for AI agents: vector search + semantic graph" \
      org.opencontainers.image.source="https://github.com/somatechlat/somafractalmemory"

# Default exposed port for API/server mode
EXPOSE 9595

# Add flexible entrypoint that maps env vars to CLI commands
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []
