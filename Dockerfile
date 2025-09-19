# syntax=docker/dockerfile:1
# Minimal Dockerfile for SomaFractalMemory - optimized for size
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt /app/requirements.txt
COPY api-requirements.txt /app/api-requirements.txt

# Install only essential Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt -r /app/api-requirements.txt && \
    # Remove unnecessary packages to reduce size
    pip uninstall -y torch torchvision torchaudio transformers && \
    # Clean up pip cache
    rm -rf /root/.cache/pip

# Copy the application code
COPY . /app

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the port
EXPOSE 9595

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9595/health || exit 1

# Default command - start the server in enterprise mode with Redis and Qdrant on default ports
CMD ["sh", "-c", "export SOMA_MODE=enterprise && uvicorn examples.api:app --host 0.0.0.0 --port 9595 --workers 2 --timeout-keep-alive 30"]
