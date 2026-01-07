# syntax=docker/dockerfile:1.6
# LIGHTWEIGHT Django-only Dockerfile for SomaFractalMemory
FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal system deps (no build-essential - use precompiled wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies directly with pip
COPY api-requirements.txt /app/

RUN pip install --no-cache-dir -r api-requirements.txt

# Copy application source - ONLY essential files
COPY somafractalmemory/ ./somafractalmemory/
COPY common/ ./common/
COPY scripts/ ./scripts/
COPY manage.py ./

RUN chmod +x /app/scripts/docker-entrypoint.sh || true
RUN chmod +x /app/scripts/bootstrap.sh

# Create non-root user
RUN useradd --create-home --uid 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 10101

CMD ["bash", "/app/scripts/bootstrap.sh"]
