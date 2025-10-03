# syntax=docker/dockerfile:1
# Minimal Dockerfile to run the FastAPI example
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (build tools and curl for health/metrics checks)
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# Install netcat for scripts that need to probe other containers
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Install procps to provide sysctl binary for adjusting kernel parameters inside containers
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY api-requirements.txt /app/api-requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt -r /app/api-requirements.txt

COPY . /app

RUN chmod +x /app/scripts/docker-entrypoint.sh

EXPOSE 9595

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:9595/healthz || exit 1

# Default command (API entrypoint) – can be overridden by docker compose for consumer etc.
CMD ["/app/scripts/docker-entrypoint.sh"]
