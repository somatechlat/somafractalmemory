# syntax=docker/dockerfile:1
# Minimal Dockerfile to run the FastAPI example
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (build tools and curl for health/metrics checks)
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY api-requirements.txt /app/api-requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt -r /app/api-requirements.txt

COPY . /app

EXPOSE 9595

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:9595/healthz || exit 1

# Default command (can be changed as needed)
CMD ["uvicorn", "examples.api:app", "--host", "0.0.0.0", "--port", "9595", "--workers", "2", "--timeout-keep-alive", "30"]
